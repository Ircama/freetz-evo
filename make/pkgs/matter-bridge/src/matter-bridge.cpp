/*
 * matter-bridge - native Matter WebSocket server for Domoticz (no Node.js).
 *
 * Domoticz' Matter hardware driver (hardware/Matter.cpp) is a WebSocket client
 * which talks to a Matter controller on port 5580 using the python-matter-server
 * JSON API:
 *
 *   server -> client  {"event":"server_info","data":{...}}              (connect)
 *   client -> server  {"message_id":"N","command":"<cmd>","args":{...}}
 *   server -> client  {"message_id":"N","result": ...}
 *   server -> client  {"message_id":"N","error_code":N,"details":"..."}
 *   server -> client  {"event":"attribute_updated","data":[node,"ep/cl/at",v]}
 *
 * This program implements that protocol natively (C++/libwebsockets/jsoncpp) so
 * that no Node.js is required on the FRITZ!Box.
 *
 * Milestone 1 (this file): complete protocol front end plus a node/attribute
 * store seeded from a JSON file, so a real Domoticz instance can be connected,
 * sees nodes, creates devices and drives them (device_command/write_attribute
 * update the store and are reported back with attribute_updated events). The
 * store is the single place where a Matter backend has to be plugged in.
 *
 * Milestone 2 (planned): exchange the store for a real Matter controller
 * (commissioning, CASE sessions, subscriptions); the protocol side stays as is.
 */
#include <libwebsockets.h>
#include <json/json.h>

#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <deque>
#include <fstream>
#include <mutex>
#include <sstream>
#include <string>
#include <vector>

/* Wire protocol constants taken from python-matter-server 8.1.2
 * (matter_server/common/const.py: SCHEMA_VERSION, matter_server/server/const.py:
 * MIN_SCHEMA_VERSION) so that any client of the reference server can talk to
 * this bridge: Home Assistant, the Domoticz Matter driver, python-matter-server
 * clients. */
#define MB_SCHEMA_VERSION     11
#define MB_MIN_SCHEMA_VERSION 9

static const char *TAG = "matter-bridge";

struct options {
	int port;
	std::string state_file;
	std::string seed_file;
	std::string sdk_version;
	bool verbose;
} g_opt = { 5580, "", "", "matter-bridge-0.1", false };

static volatile sig_atomic_t g_stop = 0;

/* ------------------------------------------------------------------ utils */

static void log_line(const char *level, const std::string &text)
{
	if (!g_opt.verbose && strcmp(level, "DEBUG") == 0)
		return;

	char stamp[32];
	time_t now = time(NULL);
	struct tm tm;
	localtime_r(&now, &tm);
	strftime(stamp, sizeof(stamp), "%Y-%m-%d %H:%M:%S", &tm);

	fprintf(stderr, "%s [%s] %s: %s\n", stamp, TAG, level, text.c_str());
	fflush(stderr);
}

static std::string to_string_int(long long value)
{
	std::ostringstream ss;
	ss << value;
	return ss.str();
}

/* ---------------------------------------------------------- json helpers */

static bool json_parse(const std::string &text, Json::Value &out)
{
	Json::CharReaderBuilder builder;
	std::string errors;
	std::unique_ptr<Json::CharReader> reader(builder.newCharReader());

	return reader->parse(text.data(), text.data() + text.size(), &out, &errors);
}

static std::string json_write(const Json::Value &value)
{
	Json::StreamWriterBuilder builder;
	builder["indentation"] = "";

	return Json::writeString(builder, value);
}

static bool read_file(const std::string &path, Json::Value &out)
{
	std::ifstream file(path.c_str(), std::ios::binary);
	if (!file.is_open())
		return false;

	std::ostringstream ss;
	ss << file.rdbuf();

	return json_parse(ss.str(), out);
}

static bool write_file(const std::string &path, const Json::Value &value)
{
	std::string tmp = path + ".tmp";
	std::ofstream file(tmp.c_str(), std::ios::binary | std::ios::trunc);
	if (!file.is_open())
		return false;

	file << json_write(value) << "\n";
	file.close();

	return rename(tmp.c_str(), path.c_str()) == 0;
}

/* --------------------------------------------------------- node storage */

static std::mutex g_store_lock;
static Json::Value g_nodes(Json::arrayValue);

static void store_load()
{
	Json::Value root;

	if (!g_opt.state_file.empty() && read_file(g_opt.state_file, root) && root.isMember("nodes")) {
		g_nodes = root["nodes"];
		log_line("INFO", "loaded " + to_string_int(g_nodes.size()) + " node(s) from " + g_opt.state_file);
		return;
	}

	if (!g_opt.seed_file.empty() && read_file(g_opt.seed_file, root) && root.isMember("nodes")) {
		g_nodes = root["nodes"];
		log_line("INFO", "seeded " + to_string_int(g_nodes.size()) + " node(s) from " + g_opt.seed_file);
		Json::Value out;
		out["nodes"] = g_nodes;
		if (!g_opt.state_file.empty() && write_file(g_opt.state_file, out))
			log_line("INFO", "initial state written to " + g_opt.state_file);
		return;
	}

	log_line("WARN", "no node store available, starting empty");
}

static void store_save()
{
	if (g_opt.state_file.empty())
		return;

	Json::Value out;
	out["nodes"] = g_nodes;
	if (!write_file(g_opt.state_file, out))
		log_line("ERROR", "cannot write " + g_opt.state_file);
}

static Json::Value *node_find(int node_id, size_t *index = NULL)
{
	for (Json::ArrayIndex i = 0; i < g_nodes.size(); i++) {
		if (g_nodes[i].isMember("node_id") && g_nodes[i]["node_id"].asInt() == node_id) {
			if (index)
				*index = i;
			return &g_nodes[i];
		}
	}

	return NULL;
}

static bool attr_read(int node_id, const std::string &path, Json::Value &out)
{
	Json::Value *node = node_find(node_id);
	if (!node || !node->isMember("attributes") || !(*node)["attributes"].isMember(path))
		return false;

	out = (*node)["attributes"][path];

	return true;
}

static bool attr_write(int node_id, const std::string &path, const Json::Value &value)
{
	size_t index = 0;
	Json::Value *node = node_find(node_id, &index);
	if (!node) {
		Json::Value created;
		created["node_id"] = node_id;
		created["attributes"] = Json::Value(Json::objectValue);
		g_nodes.append(created);
		node = node_find(node_id, &index);
		if (!node)
			return false;
		log_line("INFO", "created node " + to_string_int(node_id));
	}

	(*node)["attributes"][path] = value;

	return true;
}

/* ------------------------------------------------------------- responses */

static std::string reply_result(const std::string &message_id, const Json::Value &result)
{
	Json::Value msg;
	msg["message_id"] = message_id;
	msg["result"] = result;

	return json_write(msg);
}

static std::string reply_error(const std::string &message_id, int code, const std::string &details)
{
	Json::Value msg;
	msg["message_id"] = message_id;
	msg["error_code"] = code;
	msg["details"] = details;

	/* no "result" key: the reference ErrorResultMessage
	 * (matter_server/common/models.py) has exactly message_id, error_code and
	 * details. Clients that check result==null keep working because JsonCpp
	 * returns a null member for a missing key. */

	return json_write(msg);
}

static std::string event_attribute_updated(int node_id, const std::string &path, const Json::Value &value)
{
	Json::Value msg;
	Json::Value data(Json::arrayValue);

	/* positional array, as expected by CMatter::HandleAttributeUpdate() */
	data.append(node_id);
	data.append(path);
	data.append(value);

	msg["event"] = "attribute_updated";
	msg["data"] = data;

	return json_write(msg);
}

static void notify_changes(int node_id, const std::vector<std::string> &paths,
			   std::vector<std::string> &out)
{
	Json::Value value;

	for (size_t i = 0; i < paths.size(); i++) {
		if (attr_read(node_id, paths[i], value))
			out.push_back(event_attribute_updated(node_id, paths[i], value));
	}
}

/* -------------------------------------------------------- command tables */

static void handle_device_command(const std::string &message_id, const Json::Value &args,
				  std::vector<std::string> &out)
{
	int node_id = args.isMember("node_id") ? args["node_id"].asInt() : 0;
	int cluster_id = args.isMember("cluster_id") ? args["cluster_id"].asInt() : 0;
	int endpoint = args.isMember("endpoint_id") ? args["endpoint_id"].asInt() : 1;
	std::string command = args.isMember("command_name") ? args["command_name"].asString() : "";
	const Json::Value &payload = args["payload"];
	std::vector<std::string> changed;
	std::string prefix;

	if (node_id <= 0) {
		out.push_back(reply_error(message_id, 1, "device_command: missing node_id"));
		return;
	}

	prefix = to_string_int(endpoint) + "/" + to_string_int(cluster_id) + "/";

	log_line("DEBUG", "device_command node=" + to_string_int(node_id) + " cluster=" +
			  to_string_int(cluster_id) + " command=" + command);

	if (cluster_id == 6) { /* OnOff */
		bool state = true;
		Json::Value current;

		if (command == "Off")
			state = false;
		else if (command == "Toggle")
			state = !(attr_read(node_id, prefix + "0", current) && current.asBool());
		else if (command != "On" && command != "OnWithTimedOff") {
			out.push_back(reply_error(message_id, 2, "unsupported OnOff command: " + command));
			return;
		}

		attr_write(node_id, prefix + "0", Json::Value(state));
		changed.push_back(prefix + "0");
	} else if (cluster_id == 8) { /* LevelControl */
		int level = -1;

		if (payload.isMember("Level"))
			level = payload["Level"].asInt();
		else if (payload.isMember("0"))
			level = payload["0"].asInt();
		else if (payload.isMember("level"))
			level = payload["level"].asInt();

		if (level < 0) {
			out.push_back(reply_error(message_id, 3, "LevelControl: unsupported payload for " + command));
			return;
		}

		if (level > 254)
			level = 254;

		attr_write(node_id, prefix + "0", Json::Value(level));
		changed.push_back(prefix + "0");

		if (command == "MoveToLevelWithOnOff" || command == "MoveToLevel")
			changed.push_back(to_string_int(endpoint) + "/6/0");
	} else if (cluster_id == 1 && command == "Identify") {
		/* accepted, nothing to change in the store */
	} else {
		out.push_back(reply_error(message_id, 4, "device_command: unsupported cluster " +
						 to_string_int(cluster_id) + " / command " + command));
		return;
	}

	store_save();
	notify_changes(node_id, changed, out);
	out.push_back(reply_result(message_id, Json::Value(Json::nullValue)));
}

static void handle_write_attribute(const std::string &message_id, const Json::Value &args,
				   std::vector<std::string> &out)
{
	std::string path = args.isMember("attribute_path") ? args["attribute_path"].asString() : "";
	int node_id = args.isMember("node_id") ? args["node_id"].asInt() : 0;

	if (path.empty()) {
		out.push_back(reply_error(message_id, 1, "write_attribute: missing attribute_path"));
		return;
	}

	if (node_id <= 0) {
		/* some clients pass "node/endpoint/cluster/attribute" instead */
		size_t first = path.find('/');
		size_t second = (first == std::string::npos) ? std::string::npos : path.find('/', first + 1);
		if (second != std::string::npos && path.find('/', second + 1) == std::string::npos) {
			node_id = atoi(path.substr(0, first).c_str());
			path = path.substr(first + 1);
		}
	}

	if (node_id <= 0 && g_nodes.size() > 0 && g_nodes[0].isMember("node_id"))
		node_id = g_nodes[0]["node_id"].asInt();

	if (node_id <= 0) {
		out.push_back(reply_error(message_id, 1, "write_attribute: cannot determine node_id"));
		return;
	}

	attr_write(node_id, path, args["value"]);
	store_save();

	std::vector<std::string> changed;
	changed.push_back(path);
	notify_changes(node_id, changed, out);

	log_line("DEBUG", "write_attribute node=" + to_string_int(node_id) + " path=" + path);

	out.push_back(reply_result(message_id, Json::Value(Json::nullValue)));
}

static void handle_get_nodes(const std::string &message_id, std::vector<std::string> &out)
{
	Json::Value result(Json::arrayValue);

	for (Json::ArrayIndex i = 0; i < g_nodes.size(); i++)
		result.append(g_nodes[i]);

	out.push_back(reply_result(message_id, result));
}

static void handle_read_attribute(const std::string &message_id, const Json::Value &args,
				  std::vector<std::string> &out)
{
	int node_id = args.isMember("node_id") ? args["node_id"].asInt() : 0;
	std::string path = args.isMember("attribute_path") ? args["attribute_path"].asString() : "";
	Json::Value value;

	/* error codes follow matter_server/common/errors.py: 8 = InvalidArguments,
	 * 5 = NodeNotExists */
	if (node_id <= 0 || path.empty()) {
		out.push_back(reply_error(message_id, 8,
					  "read_attribute: node_id and attribute_path are required"));
		return;
	}
	if (!attr_read(node_id, path, value)) {
		out.push_back(reply_error(message_id, 5, "read_attribute: no attribute " + path +
					  " on node " + to_string_int(node_id)));
		return;
	}
	out.push_back(reply_result(message_id, value));
}

static void handle_start_listening(const std::string &message_id, std::vector<std::string> &out)
{
	Json::Value result(Json::arrayValue);

	for (Json::ArrayIndex i = 0; i < g_nodes.size(); i++)
		result.append(g_nodes[i]);

	log_line("INFO", "start_listening: " + to_string_int(result.size()) + " node(s) reported");
	out.push_back(reply_result(message_id, result));
}

/* Commands of the python-matter-server API which require a real Matter
 * controller. They are answered with a clear error so Domoticz reports a
 * failure instead of hanging, and they mark where milestone 2 hooks in. */
static const char *g_pending_commands[] = {
	"commission_with_code", "commission_on_network", "open_commissioning_window",
	"interview_node", "remove_node", "set_thread_dataset", "set_wifi_credentials",
	"set_default_fabric_label", "get_node_ip_addresses", "ping_node",
	NULL
};

static bool command_is_pending(const std::string &command)
{
	for (int i = 0; g_pending_commands[i]; i++) {
		if (command == g_pending_commands[i])
			return true;
	}

	return false;
}

/* The reference server sends an unsolicited *flat* ServerInfoMessage frame as
 * the very first message (see matter_server/client/connection.py: "at connect,
 * the server sends a single message with the server info" and the MessageType
 * union in common/models.py). Clients such as the Domoticz Matter driver detect
 * it by looking for a top-level sdk_version, so it must not be wrapped in an
 * event envelope. */
static std::string server_info_message()
{
	Json::Value data;

	data["fabric_id"] = 1;
	data["compressed_fabric_id"] = 1;
	data["schema_version"] = MB_SCHEMA_VERSION;
	data["min_supported_schema_version"] = MB_MIN_SCHEMA_VERSION;
	data["sdk_version"] = g_opt.sdk_version;
	data["wifi_credentials_set"] = false;
	data["thread_credentials_set"] = false;
	data["bluetooth_enabled"] = false;

	return json_write(data);
}

static Json::Value server_info_value()
{
	Json::Value info;

	info["fabric_id"] = 1;
	info["compressed_fabric_id"] = 1;
	info["schema_version"] = MB_SCHEMA_VERSION;
	info["min_supported_schema_version"] = MB_MIN_SCHEMA_VERSION;
	info["sdk_version"] = g_opt.sdk_version;
	info["wifi_credentials_set"] = false;
	info["thread_credentials_set"] = false;
	info["bluetooth_enabled"] = false;

	return info;
}

static void handle_message(const std::string &text, std::vector<std::string> &out)
{
	Json::Value msg;

	if (!json_parse(text, msg) || !msg.isObject()) {
		log_line("ERROR", "cannot parse incoming message");
		return;
	}

	std::string message_id = msg.isMember("message_id") ? msg["message_id"].asString() : "0";
	std::string command = msg.isMember("command") ? msg["command"].asString() : "";

	if (command.empty()) {
		log_line("WARN", "message without command");
		return;
	}

	std::lock_guard<std::mutex> guard(g_store_lock);

	if (command == "start_listening") {
		handle_start_listening(message_id, out);
	} else if (command == "get_nodes") {
		handle_get_nodes(message_id, out);
	} else if (command == "read_attribute") {
		handle_read_attribute(message_id, msg["args"], out);
	} else if (command == "device_command") {
		handle_device_command(message_id, msg["args"], out);
	} else if (command == "write_attribute") {
		handle_write_attribute(message_id, msg["args"], out);
	} else if (command == "server_info" || command == "get_server_info") {
		out.push_back(reply_result(message_id, server_info_value()));
	} else if (command_is_pending(command)) {
		log_line("WARN", "command '" + command + "' needs the Matter controller backend (not implemented yet)");
		out.push_back(reply_error(message_id, 9, "matter-bridge: '" + command +
						  "' requires the Matter controller backend, which is not implemented in this build"));
	} else {
		log_line("WARN", "unknown command '" + command + "'");
		out.push_back(reply_error(message_id, 9, "matter-bridge: unknown command '" + command + "'"));
	}
}

/* --------------------------------------------------------- lws callbacks */

/* libwebsockets zeroes the per-session buffer without running constructors, so
 * only trivially zero-initialisable members are allowed here: the queue is
 * allocated on LWS_CALLBACK_ESTABLISHED and freed on LWS_CALLBACK_CLOSED. */
struct per_session_data {
	std::deque<std::string> *queue;
};

static int callback_matter(struct lws *wsi, enum lws_callback_reasons reason,
			   void *user, void *in, size_t len)
{
	struct per_session_data *psd = (struct per_session_data *)user;
	std::vector<std::string> responses;

	switch (reason) {
	case LWS_CALLBACK_ESTABLISHED:
		if (!psd->queue)
			psd->queue = new std::deque<std::string>();
		psd->queue->push_back(server_info_message());
		lws_callback_on_writable(wsi);
		log_line("INFO", "client connected");
		break;

	case LWS_CALLBACK_RECEIVE: {
		std::string text((const char *)in, len);
		handle_message(text, responses);
		if (psd->queue && !responses.empty()) {
			for (size_t i = 0; i < responses.size(); i++)
				psd->queue->push_back(responses[i]);
			lws_callback_on_writable(wsi);
		}
		break;
	}

	case LWS_CALLBACK_SERVER_WRITEABLE:
		/* exactly one JSON document per WebSocket frame: clients like the
		 * Domoticz Matter driver parse a single message per frame */
		if (psd->queue && !psd->queue->empty()) {
			std::string &msg = psd->queue->front();
			std::vector<unsigned char> buffer(LWS_PRE + msg.size());

			memcpy(buffer.data() + LWS_PRE, msg.data(), msg.size());

			int written = lws_write(wsi, buffer.data() + LWS_PRE, msg.size(), LWS_WRITE_TEXT);
			if (written < (int)msg.size()) {
				if (written > 0)
					msg.erase(0, written);
				lws_callback_on_writable(wsi);
				break;
			}
			psd->queue->pop_front();
			if (!psd->queue->empty())
				lws_callback_on_writable(wsi);
		}
		break;

	case LWS_CALLBACK_CLOSED:
		if (psd->queue) {
			delete psd->queue;
			psd->queue = NULL;
		}
		log_line("INFO", "client disconnected");
		break;

	default:
		break;
	}

	return 0;
}

static struct lws_protocols g_protocols[] = {
	{ "matter-bridge", callback_matter, sizeof(struct per_session_data), 0, 0, NULL, 0 },
	{ NULL, NULL, 0, 0, 0, NULL, 0 }
};

/* ------------------------------------------------------------------ main */

static void on_signal(int sig)
{
	(void)sig;
	g_stop = 1;
}

static void usage(const char *argv0)
{
	fprintf(stderr,
		"Usage: %s [options]\n"
		"  -p, --port <port>       WebSocket port (default 5580)\n"
		"  -n, --nodes <file>      persistent node store (JSON)\n"
		"  -s, --seed <file>       initial node store, copied on first start\n"
		"  -d, --sdk-version <v>   string reported as sdk_version\n"
		"  -v, --verbose           verbose logging (also enables libwebsockets logs)\n"
		"  -h, --help              this text\n",
		argv0);
}

int main(int argc, char **argv)
{
	for (int i = 1; i < argc; i++) {
		std::string arg = argv[i];

		if ((arg == "-p" || arg == "--port") && i + 1 < argc)
			g_opt.port = atoi(argv[++i]);
		else if ((arg == "-n" || arg == "--nodes") && i + 1 < argc)
			g_opt.state_file = argv[++i];
		else if ((arg == "-s" || arg == "--seed") && i + 1 < argc)
			g_opt.seed_file = argv[++i];
		else if ((arg == "-d" || arg == "--sdk-version") && i + 1 < argc)
			g_opt.sdk_version = argv[++i];
		else if (arg == "-v" || arg == "--verbose")
			g_opt.verbose = true;
		else if (arg == "-h" || arg == "--help") {
			usage(argv[0]);
			return 0;
		} else {
			fprintf(stderr, "%s: unknown argument '%s'\n", TAG, arg.c_str());
			usage(argv[0]);
			return 1;
		}
	}

	if (!g_opt.verbose)
		lws_set_log_level(LLL_ERR | LLL_WARN, NULL);

	signal(SIGINT, on_signal);
	signal(SIGTERM, on_signal);
	signal(SIGPIPE, SIG_IGN);

	{
		std::lock_guard<std::mutex> guard(g_store_lock);
		store_load();
	}

	struct lws_context_creation_info info;
	memset(&info, 0, sizeof(info));
	info.port = g_opt.port;
	info.protocols = g_protocols;
	info.gid = -1;
	info.uid = -1;
	info.options = LWS_SERVER_OPTION_VALIDATE_UTF8;

	struct lws_context *context = lws_create_context(&info);
	if (!context) {
		log_line("ERROR", "cannot create WebSocket context on port " + to_string_int(g_opt.port));
		return 1;
	}

	log_line("INFO", "listening on port " + to_string_int(g_opt.port) + " (schema " +
			  to_string_int(MB_SCHEMA_VERSION) + ")");

	while (!g_stop)
		lws_service(context, 0);

	lws_context_destroy(context);
	log_line("INFO", "stopped");

	return 0;
}
