#ifndef LIBUDEV_H
#define LIBUDEV_H

#include <sys/types.h>

struct udev;
struct udev_device;
struct udev_enumerate;

struct udev_list_entry {
	char *name;
	struct udev_list_entry *next;
};

#define udev_list_entry_foreach(list_entry, first_entry) \
	for (list_entry = (first_entry); list_entry; \
	     list_entry = udev_list_entry_get_next(list_entry))

struct udev *udev_new(void);
struct udev *udev_ref(struct udev *udev);
void udev_unref(struct udev *udev);

struct udev_device *udev_device_ref(struct udev_device *dev);
void udev_device_unref(struct udev_device *dev);
const char *udev_device_get_syspath(struct udev_device *dev);
const char *udev_device_get_devnode(struct udev_device *dev);
struct udev_device *udev_device_new_from_syspath(struct udev *udev, const char *syspath);
struct udev_device *udev_device_new_from_devnum(struct udev *udev, char type, dev_t devnum);
struct udev_device *udev_device_get_parent_with_subsystem_devtype(
	struct udev_device *dev, const char *subsystem, const char *devtype);
const char *udev_device_get_sysattr_value(struct udev_device *dev, const char *sysattr);

struct udev_enumerate *udev_enumerate_new(struct udev *udev);
int udev_enumerate_add_match_subsystem(struct udev_enumerate *enumerate, const char *subsystem);
int udev_enumerate_scan_devices(struct udev_enumerate *enumerate);
struct udev_list_entry *udev_enumerate_get_list_entry(struct udev_enumerate *enumerate);
void udev_enumerate_unref(struct udev_enumerate *enumerate);

const char *udev_list_entry_get_name(struct udev_list_entry *entry);
struct udev_list_entry *udev_list_entry_get_next(struct udev_list_entry *entry);

#endif /* LIBUDEV_H */
