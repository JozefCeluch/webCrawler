#ifndef DATABASE_H_
#define DATABASE_H_

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <sqlite3.h>

#define TOOL_NAME "Web Crawler"
#define TOOL_VERSION "0.1"
#define DEST_PROJECT "Linux Kernel"
#define ERR_TYPE "BUG/WARNING"
/*! \def MAX_SQL_STMT_LEN 120
    \brief Maximum length of sql statement
*/
#define MAX_SQL_STMT_LEN 120

/*! \struct sqlStmt
    \brief Contains all prepared sql statements and database connection.

 */
struct sqlStmt
{
	sqlite3_stmt *sql_err;
	sqlite3_stmt *sql_rel;
	sqlite3_stmt *sql_select;
	sqlite3 *db;
};

/*! \struct db
    \brief Contains values that are inserted into database.

 */
struct db
{
	char *tool_name;
	char *tool_ver;
	char *dest_proj;
	char *error_type;
	char *user;
	int tool_id;
	int user_id;
	int error_type_id;
	int proj_id;
	char *project_ver;
	char *loc_file;
	char *loc_line;
	char *url;
};

/*! \fn void sql_init(struct sqlStmt *data, struct db *database)
    \brief Initializes sql statements.
    \param data Structure containing uninitializes sql statements.
    \param database Uninitialized database connection.

    \return -1 error
    \return 0 OK
*/
void sql_init(struct sqlStmt *data, struct db *database, char *db_file);

/*! \fn void insert_to_db(sqlite3 **db, struct sqlStmt *data, struct db *database)
    \brief Inserts data into the database.
    \param db Pointer to initialized database connection.
    \param data Structure containing compiled sql statements.
    \param database Structure containing data to be inserted into database.

    \return -1 error
    \return 0 item already in database
    \return 1 new item inserted into database
*/
int insert_to_db(sqlite3 **db, struct sqlStmt *data, struct db *database);

/*! \fn int get_id (sqlite3 *db, char *table, char *column, char* value)
    \brief Returns id of column with value from table.
    \param db Pointer to initialized database connection.
    \param table Table name.
    \param column Column name.
    \param value Searched value.

    \return id number if found, 0 otherwise
*/
int get_id (sqlite3 *db, char *table, char *column, char* value);

		/* TODO: missing error_subtype */
/*! \fn int check_duplicates(sqlite3_stmt *stmt, int error_type, int project, char *project_version,
  				char *loc_file, char *loc_line)
    \brief Checks for duplicates.
    \param stmt Compiled sql statment.
    \param error_type Error type number.
    \param project Project number.
    \param project_version Project version string.
    \param loc_file Loc file string.
    \param loc_line Loc line string.

    \return 0 no duplicate
    \return 1 entry already in the database
*/
int check_duplicates(sqlite3_stmt *stmt, int error_type, int project, char *project_version,
		char *loc_file, char *loc_line);

		/* TODO: missing error_subtype */
/*! \fn int insert_error(sqlite3_stmt *stmt, int user, int error_type, int project,
		char *project_version, char *loc_file, char *loc_line,
		char *url)
    \brief Inserts data into error table.
    \param stmt Compiled sql statment.
    \param user User id number.
    \param error_type Error type number.
    \param project Project number.
    \param project_version Project version string.
    \param loc_file Loc file string.
    \param loc_line Loc line string.
    \param url Url where entry was found.
    \return sqlite3_step return value
*/
int insert_error(sqlite3_stmt *stmt, int user, int error_type, int project,
		char *project_version, char *loc_file, char *loc_line,
		char *url);

/*! \fn insert_tool_rel(sqlite3_stmt *stmt, int tool_id, int error_id)
    \brief Inserts data into tool_rel table.
    \param stmt Compiled sql statment.
    \param tool_id Tool id number.
    \param error_id Error id number.
    \return sqlite3_step return value
*/
int insert_tool_rel(sqlite3_stmt *stmt, int tool_id, int error_id);


#endif /* DATABASE_H_ */
