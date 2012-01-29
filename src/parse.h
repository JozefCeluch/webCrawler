#ifndef PARSE_H_
#define PARSE_H_
#include <libxml/HTMLparser.h>
#include <libxml/xmlmemory.h>
#include <libxml/parser.h>
#include <pcre.h>
#include "database.h"

#define OVECCOUNT 15    /* should be a multiple of 3, for n groups: (n+1)*3 */
#define URL_SIZE 70

// struct to contain contents of curl retrievals
struct htmlData
{
	char *page;
	size_t size;
};

struct parsingData
{
	pcre *re_bug;
	pcre *re_pid;
	pcre *re_path;
	struct sqlStmt sql;
	struct db database;
};

int compile_regex(pcre **re, char *regex);

/*
 * Runs regex matching
 * returns pcre_exec return value
 */
int match_regex(char *string, pcre *re, int **ovector);

/*
 * Sets and runs parser to convert HTML to XML
 */
int convert_html(struct htmlData *chunk, htmlParserCtxtPtr *parser);

/*
 * Crawls the XML tree, looking for pre elements
 */
int parse_xml(xmlNodePtr root_node, struct parsingData *parse);

/*
 * Runs both regexes on the string
 * returns >0 if both regexes found match in string
 */
int bug_warning_match(char* string, struct parsingData *data);

/*
 * Prints results of regex maching
 * success 1, otherwise 0
 */
int print_regex_result(char *string, int stat1, int *ovector1, int stat2,
		int *ovector2, struct parsingData *parse);

#endif /* PARSE_H_ */
