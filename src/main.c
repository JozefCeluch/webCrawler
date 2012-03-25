#include <errno.h>
#include "network.h"

void die(const char *error)
{
	fprintf(stderr, "webCrawler: %s\n", error);
	exit(EXIT_FAILURE);
}


char *read_line(FILE *url_file)
{
	char *url = NULL;
	size_t len = 0;
	ssize_t read;

	if ((read = getline(&url, &len, url_file)) != -1) {
		url[read - 1] = '\0';
		return url;
	} else {
		free(url);
		return NULL;
	}
}

/*
 * QUESTION
 * co robit, ak v samotnom texte commentu nie su obidva udaje, ale je v nom prilozeny kompletny log ako attachment?
 * napr.:
 * https://bugzilla.novell.com/show_bug.cgi?id=551948
 * https://bugzilla.novell.com/show_bug.cgi?id=599628
 */

/*
 * TODO fix return values of all functions
 * 0 OK; >0 amount/success message, etc.; <0 error
 */

int main(int argc, char *argv[])
{
	CURL *curl = NULL;
	FILE *fd;
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

	struct htmlData chunk;
	struct parsingData data;

	sql_init(&data.sql, &data.database);
	LIBXML_TEST_VERSION;

	char *regex_path =
			"s|^/usr/src/packages/BUILD/(?:kernel-[a-z]+-[0-9.]+/linux-[0-9.]+/)?||";
	char *regex_part1 =
			"(?:WARNING:|kernel\\s+BUG)\\s+at\\s+(\\S+)\\s?:([0-9]+)!?";
	char *regex_pid =
			"Pid:\\s+[0-9]+,\\s+comm:\\s+.{1,20}\\s+(?:Not\\s+tainted|Tainted:\\s+[A-Z ]+)\\s+\\(?([0-9.-]+\\S+)\\s+#";

	compile_regex(&data.re_bug, regex_part1);
	compile_regex(&data.re_pid, regex_pid);
	compile_regex(&data.re_path, regex_path);

	if (argc == 2) {
		file_name = argv[1];
	} else {
		file_name = "bnc-bug-at.txt";
	}

	fd = fopen(file_name, "r");
	if (fd == NULL) {
		die("Error, opening file");
	}

	download_failed = fopen("failed_download_urls", "a+");
	if (download_failed == NULL) {
		die("Error, creating file");
	}

	regex_failed = fopen("failed_regex_urls", "a+");
	if (regex_failed == NULL) {
		die("Error, creating file");
	}

	while ((data.database.url = read_line(fd)) != NULL) {
		chunk.page = NULL;
		chunk.size = 0;
		++url_count;
//		data.database.url = "https://bugzilla.novell.com/show_bug.cgi?id=648118";
		printf("%d. Fetching %s\n", url_count, data.database.url);
		match_count = 0;

		if (!initialize_curl(&curl, data.database.url, &chunk, error_buffer)) {
			parser = htmlCreatePushParserCtxt(NULL, NULL, NULL, 0, NULL, 0);
			convert_html(&chunk, &parser);
			if (parser) {
				match_count = parse_xml(xmlDocGetRootElement(parser->myDoc), &data);
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
		} else {
			printf("Download failed\n");
			++failed_dwnld_count;
			fprintf(download_failed, "%s\n", data.database.url);
		}
		free(data.database.url);
	}
	printf("\nALL URLs:\t\t%d\nSUCCESSFUL MATCH:\t%d\nNEW DB ENTRIES:\t\t%d\
			\nFAILED DOWNLOAD:\t%d\nFAILED REGEX:\t\t%d\n", url_count,
			success_regex_count, success_db_insert, failed_dwnld_count, failed_regex_count);

	xmlCleanupParser();
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
