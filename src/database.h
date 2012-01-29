#ifndef DATABASE_H_
#define DATABASE_H_

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <sqlite3.h>

#define MAX_SQL_STMT_LEN 80

struct sqlStmt
{
	sqlite3_stmt *sql_err;
	sqlite3_stmt *sql_rel;
	sqlite3_stmt *sql_select;
	sqlite3 *db;
};

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

void sql_init(struct sqlStmt *data, struct db *database);

void insert_to_db(sqlite3 **db, struct sqlStmt *data, struct db *database);

int get_id (sqlite3 *db, char *table, char *column, char* value);

/* without error_subtype */
int check_duplicates(sqlite3_stmt *stmt, int error_type, int project, char *project_version,
		char *loc_file, char *loc_line);

/* without error_subtype */
int insert_error(sqlite3_stmt *stmt, int user, int error_type, int project,
		char *project_version, char *loc_file, char *loc_line,
		char *url);

int insert_tool_rel(sqlite3_stmt *stmt, int tool_id, int error_id);


#endif /* DATABASE_H_ */
