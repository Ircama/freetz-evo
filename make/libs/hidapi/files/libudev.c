/*
 * Minimal libudev compatibility stub for embedded systems
 *
 * Provides the udev API functions needed by HIDAPI hidraw backend,
 * implemented by reading sysfs directly. This allows HIDAPI to
 * compile and work on systems without a udev daemon (e.g., busybox-based
 * embedded devices).
 *
 * SPDX-License-Identifier: MIT
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#include <dirent.h>
#include <errno.h>

#include "libudev.h"

struct udev {
	int refcount;
};

struct udev_device {
	int refcount;
	char *syspath;
	char *devnode;
};

struct udev_enumerate {
	int refcount;
	char subsystem[256];
	struct udev_list_entry *entries;
	struct udev_list_entry *last;
};

struct udev *udev_new(void)
{
	struct udev *udev = calloc(1, sizeof(*udev));
	if (udev)
		udev->refcount = 1;
	return udev;
}

struct udev *udev_ref(struct udev *udev)
{
	if (udev)
		udev->refcount++;
	return udev;
}

void udev_unref(struct udev *udev)
{
	if (!udev)
		return;
	udev->refcount--;
	if (udev->refcount <= 0)
		free(udev);
}

struct udev_device *udev_device_ref(struct udev_device *dev)
{
	if (dev)
		dev->refcount++;
	return dev;
}

void udev_device_unref(struct udev_device *dev)
{
	if (!dev)
		return;
	dev->refcount--;
	if (dev->refcount > 0)
		return;
	free(dev->syspath);
	free(dev->devnode);
	free(dev);
}

const char *udev_device_get_syspath(struct udev_device *dev)
{
	return dev ? dev->syspath : NULL;
}

const char *udev_device_get_devnode(struct udev_device *dev)
{
	return dev ? dev->devnode : NULL;
}

struct udev_device *udev_device_new_from_syspath(struct udev *udev,
						  const char *syspath)
{
	struct udev_device *dev;

	if (!udev || !syspath)
		return NULL;

	dev = calloc(1, sizeof(*dev));
	if (!dev)
		return NULL;

	dev->refcount = 1;
	dev->syspath = strdup(syspath);

	return dev;
}

struct udev_device *udev_device_new_from_devnum(struct udev *udev,
						 char type, dev_t devnum)
{
	(void)type;
	(void)devnum;
	/* Simplified: return a basic device from sysfs hidraw path */
	return udev_device_new_from_syspath(udev, "/sys/class/hidraw");
}

struct udev_device *udev_device_get_parent_with_subsystem_devtype(
	struct udev_device *dev,
	const char *subsystem,
	const char *devtype)
{
	char path[512];
	char resolved[512];
	ssize_t len;
	struct udev_device *parent;
	char *syspath;

	(void)devtype;

	if (!dev || !dev->syspath || !subsystem)
		return NULL;

	syspath = strdup(dev->syspath);
	if (!syspath)
		return NULL;

	/* Walk up the directory tree looking for subsystem match */
	while (1) {
		char *last_slash = strrchr(syspath, '/');
		if (!last_slash || last_slash == syspath)
			break;
		*last_slash = 0;

		snprintf(path, sizeof(path), "%s/subsystem", syspath);
		len = readlink(path, resolved, sizeof(resolved) - 1);
		if (len > 0) {
			resolved[len] = 0;
			const char *subsys_name = strrchr(resolved, '/');
			if (subsys_name)
				subsys_name++;
			else
				subsys_name = resolved;

			if (strcmp(subsys_name, subsystem) == 0) {
				parent = calloc(1, sizeof(*parent));
				if (parent) {
					parent->refcount = 1;
					parent->syspath = strdup(syspath);
				}
				free(syspath);
				return parent;
			}
		}
	}

	free(syspath);
	return NULL;
}

const char *udev_device_get_sysattr_value(struct udev_device *dev,
					   const char *sysattr)
{
	static char buf[4096];
	char path[512];
	FILE *f;

	if (!dev || !dev->syspath || !sysattr)
		return NULL;

	/* Try direct attribute path */
	snprintf(path, sizeof(path), "%s/%s", dev->syspath, sysattr);
	f = fopen(path, "r");
	if (!f) {
		/* Try with device/ prefix */
		snprintf(path, sizeof(path), "%s/device/%s",
			 dev->syspath, sysattr);
		f = fopen(path, "r");
	}
	if (!f)
		return NULL;

	if (!fgets(buf, sizeof(buf), f)) {
		fclose(f);
		return NULL;
	}
	fclose(f);

	buf[strcspn(buf, "\n")] = 0;
	return buf;
}

struct udev_enumerate *udev_enumerate_new(struct udev *udev)
{
	struct udev_enumerate *enumerate;

	if (!udev)
		return NULL;

	enumerate = calloc(1, sizeof(*enumerate));
	if (enumerate)
		enumerate->refcount = 1;
	return enumerate;
}

int udev_enumerate_add_match_subsystem(struct udev_enumerate *enumerate,
					const char *subsystem)
{
	if (!enumerate || !subsystem)
		return -1;
	strncpy(enumerate->subsystem, subsystem,
		sizeof(enumerate->subsystem) - 1);
	enumerate->subsystem[sizeof(enumerate->subsystem) - 1] = 0;
	return 0;
}

int udev_enumerate_scan_devices(struct udev_enumerate *enumerate)
{
	char path[512];
	DIR *dir;
	struct dirent *entry;
	struct udev_list_entry *le;

	if (!enumerate || !enumerate->subsystem[0])
		return -1;

	/* Clear previous entries */
	while (enumerate->entries) {
		le = enumerate->entries;
		enumerate->entries = le->next;
		free(le->name);
		free(le);
	}
	enumerate->last = NULL;

	snprintf(path, sizeof(path), "/sys/class/%s", enumerate->subsystem);
	dir = opendir(path);
	if (!dir)
		return 0;

	while ((entry = readdir(dir)) != NULL) {
		if (entry->d_name[0] == '.')
			continue;

		le = calloc(1, sizeof(*le));
		if (!le)
			continue;
		snprintf(path, sizeof(path), "/sys/class/%s/%s",
			 enumerate->subsystem, entry->d_name);
		le->name = strdup(path);
		le->next = NULL;

		if (enumerate->last)
			enumerate->last->next = le;
		else
			enumerate->entries = le;
		enumerate->last = le;
	}
	closedir(dir);

	return 0;
}

struct udev_list_entry *udev_enumerate_get_list_entry(
	struct udev_enumerate *enumerate)
{
	return enumerate ? enumerate->entries : NULL;
}

void udev_enumerate_unref(struct udev_enumerate *enumerate)
{
	struct udev_list_entry *le;

	if (!enumerate)
		return;
	enumerate->refcount--;
	if (enumerate->refcount > 0)
		return;

	while (enumerate->entries) {
		le = enumerate->entries;
		enumerate->entries = le->next;
		free(le->name);
		free(le);
	}
	free(enumerate);
}

const char *udev_list_entry_get_name(struct udev_list_entry *entry)
{
	return entry ? entry->name : NULL;
}

struct udev_list_entry *udev_list_entry_get_next(
	struct udev_list_entry *entry)
{
	return entry ? entry->next : NULL;
}
