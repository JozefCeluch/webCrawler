/*! \file parse.h
    \brief Header contaning parsing related functions.

    Contains definitions of structures and functions that handle html conversion and parsing
*/

#ifndef PARSE_H_
#define PARSE_H_
#include <libxml/HTMLparser.h>
#include <libxml/xmlmemory.h>
#include <libxml/parser.h>
#include <pcre.h>
#include "database.h"

/*! \def OVECCOUNT 15
    \brief Size of pcre ovector

    Should be a multiple of 3, for n groups (n+1)*3.
*/
#define OVECCOUNT 15

/*! \def URL_SIZE 120
    \brief Length of url.

*/
#define URL_SIZE 250

/*! \struct htmlData
    \brief Contains data and size downloaded by CURL library.

 */
struct htmlData
{
	char *page;
	size_t size;
};

/*! \struct parsingData
    \brief Contains all structures needed for parsing.

    There are pointers to compiled regular expressions and also all the information
    needed to access the database.
 */
struct parsingData
{
	pcre *re_bug;
	pcre *re_pid;
	pcre *re_path;
	struct sqlStmt sql;
	struct db database;
};

/*! \fn int compile_regex(pcre **re, char *regex)
    \brief Compiles the regular expression.
    \param re Compiled regular expression.
    \param regex Regular expression string.
    \return 0 OK
    \return -1 No regex string was passed
    \return -2 Regex compilation error
*/
int compile_regex(pcre **re, char *regex);

/*! \fn int match_regex(char *string, pcre *re, int **ovector)
    \brief Runs regex matching.
    \param string String to match regex against.
    \param re Compiled regular expression.
    \param ovector Output vector for substiong information.
    \return pcre_exec return value if OK
    \return 1 on parameter error
  */
int match_regex(char *string, pcre *re, int **ovector);

/*! \fn int convert_html(struct htmlData *chunk, htmlParserCtxtPtr *parser)
    \brief Sets and runs parser to convert HTML to XML.
    \param chunk Data structure containing data for conversion.
    \param parser Initialized HTML parser.
    \return 0 OK
 */
int convert_html(struct htmlData *chunk, htmlParserCtxtPtr *parser);

/*! \fn int parse_xml(xmlNodePtr root_node, struct parsingData *parse)
    \brief Crawls the XML tree, looking for "pre" elements.
    \param root_node Root node of XML tree.
    \param parse Structure containing all parsing information.
    \return -1 No match found.
    \return 0 All matches found are already in the database.
    \return >0 Number of new items inserted to database.
 */
int parse_xml(xmlNodePtr root_node, struct parsingData *parse);

/*! \fn int bug_warning_match(char* string, struct parsingData *data)
    \brief Runs both regexes on the string.
    \param string String to match regular expressions against.
    \param data Structure containing parsing information.
    \return -2 Error.
    \return -1 No match found.
    \return 0 Item is already in the database.
    \return 1 New item added into the database.
 */
int bug_warning_match(char* string, struct parsingData *data);

/*! \fn int print_regex_result(char *string, int stat1, int *ovector1, int stat2,\
			int *ovector2, struct parsingData *parse)
   \brief Prints results of regex matching and saves them to database.
   \param string Whole string.
   \param stat1 Position of first match in ovector
   \param ovector1 Ovector of first regex match
   \param stat2 Position of second match in ovector
   \param ovector2 Ovector of second regex match
   \param parse Structure containig parsing data
   \return -1 Parameter error.
   \return 0 Item is already in the database.
   \return 1 New item added to the database.
 */
int print_regex_result(char *string, int stat1, int *ovector1, int stat2,
		int *ovector2, struct parsingData *parse);

#endif /* PARSE_H_ */
