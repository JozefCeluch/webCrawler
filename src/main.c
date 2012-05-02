#include <errno.h>
#include <signal.h>
#include <unistd.h>
#include "network.h"

volatile int end = 0;

void die(const char *error)
{
	fprintf(stderr, "webCrawler: %s\n", error);
	exit(EXIT_FAILURE);
}

void handle_quit()
{
	end = 1;
}

void sig_prep()
{
	struct sigaction quit;
	sigemptyset(&quit.sa_mask);
	quit.sa_flags = 0;
	quit.sa_handler = handle_quit;
	sigaction(SIGINT, &quit, NULL);
	sigaction(SIGTSTP, &quit, NULL);
	sigaction(SIGKILL, &quit, NULL);
	sigaction(SIGQUIT, &quit, NULL);
	sigaction(SIGTERM, &quit, NULL);
}

/*
	Searches for *name in *in_str and copies the value associated to that name
	to **ret_value.
	Original input string is left intact.
*/
int get_list_value(char *in_list, char* name, char **ret_value)
{
	char *str, *subtoken, *saveptr;
	char *begin_q=NULL, *end_q=NULL, *loc=NULL;
	char name_q[strlen(name) + 3];
	int copied = 0;
	int len;
	char *list = NULL;
	if (in_list == NULL || name == NULL) {
		return -1;
	}
	list = strdup(in_list);
	if (list == NULL){
		fprintf(stderr, "strdup() failed\n");
		return -1;
	}
	if (list[0] == '{') memmove(list, list+1, strlen(list));

	sprintf(name_q, "\"%s\"", name);
	for (str = list;; str = NULL) {
		subtoken = strtok_r(str, ",", &saveptr);
		if (subtoken == NULL || copied)
			break;
		if ((loc = strstr(subtoken, name_q))) {
			begin_q = strchr(&loc[strlen(name_q)+1], '\"');
			end_q = strrchr(subtoken, '\"');
			len = end_q - begin_q-1;
			printf("length %d\n", len);
			if (len > 0) {
				*ret_value = strndup(begin_q+1, len);
				copied = 1;
			}
		}
	}
	free(list);
	printf("Split list finished\n");
	if (!copied)
		return -1;
	return 0;
};

int get_sublist(char *in_list, char* name, char **ret_value)
{
	char *str;
	char *begin_sub = NULL, *end_sub = NULL;
	char *next_comma = NULL;
	char name_q[strlen(name) + 3];
	int copied = 0;
	int len;
	char *list = NULL;

	if (in_list == NULL || name == NULL) {
		return -1;
	}

	list = strdup(in_list);
	if (list == NULL){
		fprintf(stderr, "strdup() failed\n");
		return -1;
	}
	if (list[0] == '{') memmove(list, list+1, strlen(list));

	sprintf(name_q, "\"%s\"", name);
	str = strstr(list, name_q);
	if (str) {
		begin_sub = strchr(&str[strlen(name_q)+1], '[');
		end_sub = strchr(begin_sub, ']');
		next_comma = strchr(&str[strlen(name_q)+1], ',');
	}

	if ((begin_sub != NULL) && (end_sub != NULL) && (next_comma == NULL || begin_sub < next_comma)){
		len = end_sub - begin_sub;
		*ret_value = strndup(begin_sub, len+1);
		copied = 1;
	}
	free(list);
	if (!copied)
		return -1;
	return 0;
}

//TODO FIX!!!!!
int scrapy_get_urls(char *jobID, FILE *fd)
{
	CURL *curl = NULL;
	char error_buffer[CURL_ERROR_SIZE];
	struct htmlData chunk;
//	struct htmlData a;
	char *url_jobs = "http://localhost:6800/listjobs.json?project=tutorial";
	//char *url_base = "http://localhost:6800/items/tutorial/%s/%s.jl";
	char url_items[URL_SIZE];
	char *spider_name = NULL;
	char *sublist = NULL;
	char *pos = NULL;
	int done = 0;
	/*
	 * this part checks every 5 seconds if passed jobID is already among
	 * finished jobs, if yes get spider_name associated with that job, else
	 * sleep 5 and try again{"url": "http://codemonkey.org.uk/2012/02/17/fedora-16-kernel-bugzilla-status-report-20120210-20120217/", "date": null, "length": 94, "num": 77}
	 */
	while (!done) {
		chunk.page = NULL;
		chunk.size = 0;
		if (initialize_curl(&curl, url_jobs, &chunk, error_buffer, NULL) < 0)
			fprintf(stderr, "CURL error\n");
		if (get_sublist(chunk.page, "finished", &sublist) < 0) {
			fprintf(stderr, "Error, scrapyd response: %s\n", chunk.page);
		} else {

			if ((pos = strstr(sublist, jobID))) {
				get_list_value(pos, "spider", &spider_name);
				done = 1;
			} else {
				printf("Sleep for 5 seconds\n");
				sleep(5);
			}
		}
//		if ((get_list_value(chunk.page, "finished", jobID, &spider_name)) < 0){
//			//sleep(5);
//		} else {
//			//break;
//		}
		free(sublist);
		free(chunk.page);
		chunk.page = NULL;
		chunk.size = 0;
	}
	curl = NULL;
	/*
	 * this part completes the request url for spider job file with jobID
	 * and then it returns the page
	 */
	sprintf(url_items, "http://localhost:6800/items/tutorial/%s/%s.jl", spider_name, jobID);
	free(spider_name);
	printf("%s\n", url_items);

	if (initialize_curl(&curl, url_items, &chunk, error_buffer, NULL) < 0){
		free(chunk.page);
		return -1;
	} else {
		fwrite(chunk.page, sizeof(char), chunk.size, fd);
		free(chunk.page);
		return 0;
	}

}

void scrapy_run_spider(char *name, char **jobID)
{
	CURL *curl = NULL;
	char error_buffer[CURL_ERROR_SIZE];
	struct htmlData chunk;
	char *url_base = "http://localhost:6800/schedule.json";
	char data[URL_SIZE];
	char *status = NULL;
	char *id = NULL;

	sprintf(data, "project=tutorial&spider=%s", name);
	printf("%s\n", data);
	chunk.page = NULL;
	chunk.size = 0;
	initialize_curl(&curl, url_base, &chunk, error_buffer, data);
	printf("data : %s\n", chunk.page);

	if (get_list_value(chunk.page, "status", &status) < 0){
		fprintf(stderr, "scrapyd response: %s\n", chunk.page);

	}
	if (get_list_value(chunk.page, "jobid", &id) < 0){
		fprintf(stderr, "jobID not found\n");
	}

	if (jobID && id) {
		strcpy(*jobID, id);
	} else {
		*jobID = NULL;
	}

	free(id);
	free(status);
	free(chunk.page);

}

char *read_file(FILE *url_file)
{
	char *line = NULL;
	char *url = NULL;
	size_t len = 0;
	ssize_t read;
	if ((read = getline(&url, &len, url_file)) < 0) {
		free(line);
		return NULL;
	} else {
//		get_list_value(line, "url", &url);
//		printf("%d\n", read);
		url[read - 1] = '\0';
//		printf("opened\n");
		free(line);
		return url;
	}
}

/*
 * TODO: add debug message macros
 */
int main(int argc, char *argv[])
{
	CURL *curl = NULL;
	FILE *fd = NULL;
	FILE *download_failed;
	FILE *regex_failed;
	int url_count = 0;
	int failed_dwnld_count = 0;
	int failed_regex_count = 0;
	int success_regex_count = 0;
	int success_db_insert = 0;

	char* file_name = NULL;
	char error_buffer[CURL_ERROR_SIZE];
	htmlParserCtxtPtr parser = NULL;
	int match_count;
	char *db_name = NULL;

	struct htmlData chunk;
	struct parsingData data;
	int opt = 0;
	if (argc < 2) {
		fprintf(stderr, "Usage: %s [-d database] [-f input_file] [-u username] \n",
							argv[0]);
		return 1;
	}
	while ((opt = getopt(argc, argv, "u:d:f:")) != -1) {
		switch (opt) {
		case 'd':
			db_name = optarg;
			break;
		case 'u':
			data.database.user = optarg;
			break;
		case 'f':
			file_name = optarg;
			break;
		default: /* '?' */
			fprintf(stderr, "Usage: %s [-d database] [-f input_file] [-u username] \n",
					argv[0]);
			exit(EXIT_FAILURE);
		}
	}

	sql_init(&data.sql, &data.database, db_name);
	LIBXML_TEST_VERSION;

	char *regex_path =
			"s|^/usr/src/packages/BUILD/(?:kernel-[a-z]+-[0-9.]+/linux-[0-9.]+/)?||";
	char *regex_part1 =
			"(?:WARNING:|kernel\\s+BUG)\\s+at\\s+(\\S+)\\s?:([0-9]+)!?";
	char
			*regex_pid =
					"Pid:\\s+[0-9]+,\\s+comm:\\s+.{1,20}\\s+(?:Not\\s+tainted|Tainted:\\s+[A-Z ]+)\\s+\\(?([0-9.-]+\\S+)\\s+#";

	compile_regex(&data.re_bug, regex_part1);
	compile_regex(&data.re_pid, regex_pid);
	compile_regex(&data.re_path, regex_path);
	sig_prep();

	//TODO add arguments parsing, usage print,
	//	if (argc == 2) {
	//		file_name = argv[1];
	//	} else {
	//		file_name = "bnc-bug-at.txt";
	//	}
	//
	fd = fopen(file_name, "rb");
	if (fd == NULL) {
		die("Error, opening file");
	}

//	scrapy_run_spider("bugzilla", &spider_id);
//	printf("%s : length = %d\n", spider_id, strlen(spider_id));
//	char *ast = "{\"url\": \"http://www.at91.com/forum/viewtopic.php/f,12/t,20179/\", \"date\": null, \"length\": 53, \"num\": 78}";
//	char *a = NULL;
//	get_list_value(ast, "url", &a);
//	return 0;
//	scrapy_get_urls(spider_id, fd);

	//free(spider_id); //somewhere later

	download_failed = fopen("failed_download_urls", "a+");
	if (download_failed == NULL) {
		die("Error, creating file");
	}

	regex_failed = fopen("failed_regex_urls", "a+");
	if (regex_failed == NULL) {
		die("Error, creating file");
	}

	rewind(fd);

	while ((data.database.url = read_file(fd)) != NULL && !end) {

		chunk.page = NULL;
		chunk.size = 0;
		++url_count;
		//		data.database.url = "https://bugzilla.novell.com/show_bug.cgi?id=648118";
		fprintf(stderr,"%d. Fetching %s\n", url_count, data.database.url);
		match_count = 0;

		if (!initialize_curl(&curl, data.database.url, &chunk,
				error_buffer, NULL)) {
			parser = htmlCreatePushParserCtxt(NULL, NULL, NULL, 0,
					NULL, 0);
			convert_html(&chunk, &parser);
			if (parser) {
				match_count = parse_xml(xmlDocGetRootElement(
						parser->myDoc), &data);
				if (match_count == -1) {
					++failed_regex_count;
					fprintf(regex_failed, "%s\n",
							data.database.url);
				} else if (match_count == 0) {
					++success_regex_count;
				} else {
					success_db_insert += match_count;
					++success_regex_count;
				}
			}
			xmlFreeDoc(parser->myDoc);
			htmlFreeParserCtxt(parser);
			free(chunk.page);
			chunk.size = 0;
		} else {
			fprintf(stderr,"Download failed\n");
			++failed_dwnld_count;
			fprintf(download_failed, "%s\n", data.database.url);
		}
		free(data.database.url);
	}
	fprintf(stderr,"FINISHED\n");
	fprintf(stderr,"NEW DB ENTRIES:\t\t%d\n", success_db_insert);
	fprintf(stderr,"SUCCESSFUL MATCH:\t%d\n", success_regex_count);
	fprintf(stderr,"FAILED REGEX:\t\t%d\n", failed_regex_count);
	fprintf(stderr,"FAILED DOWNLOAD:\t%d\n", failed_dwnld_count);
	fprintf(stderr,"ALL URLs:\t\t%d\n", url_count);
	xmlCleanupParser();
	if (fd)
		fclose(fd);
	fclose(download_failed);
	fclose(regex_failed);
	sqlite3_finalize(data.sql.sql_select);
	sqlite3_finalize(data.sql.sql_err);
	sqlite3_finalize(data.sql.sql_rel);
	sqlite3_close(data.sql.db);
	pcre_free(data.re_bug);
	pcre_free(data.re_pid);
	pcre_free(data.re_path);

	exit(EXIT_SUCCESS);
}
