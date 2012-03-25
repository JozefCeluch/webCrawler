#include "parse.h"

int compile_regex(pcre **re, char *regex)
{
	if (regex == NULL) {
		fprintf(stderr, "compile_regex parameter FAIL\n");
		return -1;
	}

	const char *error;
	int erroffset;

	*re = pcre_compile(regex, /* the pattern */
	PCRE_UCP | PCRE_NEWLINE_ANYCRLF | PCRE_CASELESS, /* options */
	&error, /* for error message */
	&erroffset, /* for error offset */
	NULL); /* use default character tables */

	if (*re == NULL) {
		printf("PCRE compilation failed at offset %d: %s\n",
				erroffset, error);
		return -2;
	}

	return 0;
}

int match_regex(char *string, pcre *re, int **ovector)
{
	if (string == NULL || re == NULL) {
		printf("match_regex parameter FAIL\n");
		return 1;
	}

	int rc;
	int string_length = strlen(string);

	rc = pcre_exec(re, /* the compiled pattern */
	NULL, /* no extra data - we didn't study the pattern */
	string, /* the subject string */
	string_length, /* the length of the subject */
	0, /* start at offset 0 in the subject */
	0, /* default options */
	*ovector, /* output vector for substring information */
	OVECCOUNT); /* number of elements in the output vector */

	/* move this out of this function */
//		if (rc < 0) {
//			switch (rc) {
//			case PCRE_ERROR_NOMATCH:
//				fprintf(stderr, "No match\n");
//				break;
//			case PCRE_ERROR_NOMEMORY:
//				fprintf(stderr, "Offset vector too small\n");
//				break;
//			case PCRE_ERROR_PARTIAL:
//				fprintf(stderr ,"Only partial match found\n");
//				break;
//			default:
//				fprintf(stderr, "Matching error %d\n", rc);
//				break;
//			}
//		}
	return rc;
}

int convert_html(struct htmlData *chunk, htmlParserCtxtPtr *parser)
{
//	htmlParserCtxtPtr
//	*parser = htmlCreatePushParserCtxt(NULL, NULL, NULL, 0, NULL, 0);

	htmlCtxtUseOptions(*parser, HTML_PARSE_NOBLANKS | HTML_PARSE_NOERROR
			| HTML_PARSE_NOWARNING | HTML_PARSE_NONET);

	htmlParseChunk(*parser, chunk->page, chunk->size, 1);
	return 0;
}

int parse_xml(xmlNodePtr root_node, struct parsingData *parse)
{
	xmlNodePtr cur_node = root_node;

	xmlChar *key = NULL;
	int found = 0;
	int process = 1;
	int match_count = 0;
	int insert_count = 0;

	/* DFS */
	printf("Parsing url\n");
	while (cur_node != NULL) {
		if (process) {
			/* to check only "pre" elements add '&& !strcmp((char *) cur_node->name, "pre")'*/
			if (cur_node->name ) {
				if (cur_node->children) {
					key = xmlNodeListGetString(
							cur_node->children->doc,
							cur_node->children, 1);
				}
				if (key) {
					found = bug_warning_match((char*) key,
							parse);
					xmlFree(key);
					key = NULL;
					switch (found) {
					case 0:
						// match found, but not inserted into db
						match_count++;
						break;
					case 1:
						// match found and inserted into db
						insert_count++;
						break;
					default:
						// no match, or other error
						break;
					}
				}
			}
		}
		if (cur_node->children != NULL && process) {
			cur_node = cur_node->children;
			process = 1;
		} else if (cur_node->next != NULL) {
			cur_node = cur_node->next;
			process = 1;
		} else {
			cur_node = cur_node->parent;
			process = 0;
		}
	}

	if (insert_count) {
		printf("New data found and inserted into database\n");
		return insert_count;
	} else if (match_count) {
		printf("Data found, already in database\n");
		return 0;
	} else {
		printf("Data not found\n");
		return -1;
	}
}

int bug_warning_match(char* string, struct parsingData *data)
{
	if (string == NULL) {
		fprintf(stderr, " ");
		return -2; // error
	}

	int res1 = 0;
	int res2 = 0;
	int *ovector1;
	int *ovector2;
	int ret_val = -1; // default value, meaning nothing was found
	//	int i = 0;
	ovector1 = malloc(sizeof(int) * OVECCOUNT);
	ovector2 = malloc(sizeof(int) * OVECCOUNT);

	res1 = match_regex(string, data->re_bug, &ovector1);
	res2 = match_regex(string, data->re_pid, &ovector2);

	if (res1 > 0 && res2 > 0) { // both regular expressions found something
		ret_val = print_regex_result(string, res1, ovector1, res2, ovector2, data);
//		result = res1 + res2;
	}

	free(ovector1);
	free(ovector2);

	return ret_val; // success: 0 already in db, 1 new db entry inserted
}

int print_regex_result(char *string, int stat1, int *ovector1, int stat2,
		int *ovector2, struct parsingData *parse)
{
	if (stat1 > 0 && stat2 > 0) {
		const char *src;
		const char *line;
		const char *ver;
		int src_offset = 0;
		int src_len = ovector1[3] - ovector1[2];
		int *vector = malloc(sizeof(int) * OVECCOUNT);
		int ret_val = 0;

		pcre_get_substring(string, ovector1, stat1, 1, &src);
		pcre_get_substring(string, ovector1, stat1, 2, &line);
		pcre_get_substring(string, ovector2, stat2, 1, &ver);

		/* keeps only last part of the path */
		if (match_regex((char *) src, parse->re_path, &vector)) {
			int i = 0, j = 0;
			while (j < 7 && i < src_len) {
				if (src[i] == '/')
					j++;
				i++;
			}
			if (i < src_len) {
				src_offset = i;
				src_len = src_len - i;
			}
		}
		parse->database.loc_file = src + src_offset;
		parse->database.loc_line = line;
		parse->database.project_ver = ver;
		printf("\t%s %s:%s\n", ver, src + src_offset, line);
		ret_val = insert_to_db(&parse->sql.db, &parse->sql, &parse->database);
		pcre_free_substring(src);
		pcre_free_substring(ver);
		pcre_free_substring(line);
		free(vector);
		return ret_val; // success: 0 already in db, 1 new db entry inserted
	} else {
		return -1; // error
	}

}
