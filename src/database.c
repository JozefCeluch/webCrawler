#include "database.h"

void sql_init(struct sqlStmt *data, struct db *database){
	const char *tail = 0;
	int rc;
	char *err_stmt =
		"INSERT INTO error(user, error_type, project, project_version, loc_file, loc_line, url) VALUES (?, ?, ?, ?, ?, ?, ?);";
	char *rel_stmt =
		"INSERT INTO error_tool_rel(tool_id, error_id) VALUES (?, ?);";
	char *select_stmt =
		"SELECT * FROM error\
		WHERE error_type=? AND project=? AND project_version=? AND loc_file = ? AND loc_line=?;";

	rc = sqlite3_open("database.db", &data->db);
	if(rc){
		fprintf(stderr, "Can not open database: %s\n", sqlite3_errmsg(data->db));
		sqlite3_close(data->db);
//		return 1;
	}

	database->tool_name = TOOL_NAME;
	database->tool_ver = TOOL_VERSION;
	database->dest_proj = DEST_PROJECT;
	database->error_type = "BUG/WARNING";
	database->user = "jirislaby";
	database->tool_id = get_id(data->db, "tool", "name", database->tool_name);
	database->user_id = get_id(data->db, "user", "login", database->user);
	database->error_type_id = get_id(data->db, "error_type", "name", database->error_type);
	database->proj_id = get_id (data->db, "project", "name", database->dest_proj);
	database->project_ver = NULL; //"2.6.31.12-0.2-xen";
	database->loc_file = NULL; //"fs/inode.c";
	database->loc_line = NULL; //"1323";
	database->url = NULL; //"https://bugzilla.novell.com/show_bug.cgi?id=648118";

	rc = sqlite3_prepare_v2(data->db, err_stmt, -1, &data->sql_err, &tail);
	if (rc != SQLITE_OK) {
		fprintf(stderr, "SQL error: %d: %s\n", rc, sqlite3_errmsg(data->db));
	}
	rc = sqlite3_prepare_v2(data->db, select_stmt, -1, &data->sql_select, &tail);
	if (rc != SQLITE_OK) {
		fprintf(stderr, "SQL error: %d: :%s\n", rc, sqlite3_errmsg(data->db));
	}
	rc = sqlite3_prepare_v2(data->db, rel_stmt, -1, &data->sql_rel, &tail);
	if (rc != SQLITE_OK) {
		fprintf(stderr, "SQL error: %d: :%s\n", rc, sqlite3_errmsg(data->db));
	}
}

int insert_to_db(sqlite3 **db, struct sqlStmt *data, struct db *database){

	int rc = 0;
	sqlite3_int64 rowid;

	rc = check_duplicates(data->sql_select, database->error_type_id,
			database->proj_id, database->project_ver, database->loc_file, database->loc_line);

	if (!rc) {
		rc = insert_error(data->sql_err, database->user_id, database->error_type_id,
				database->proj_id, database->project_ver,
				database->loc_file, database->loc_line, database->url);
		if (rc != SQLITE_DONE) {
			fprintf(stderr, "SQL insert error: %d: :%s\n", rc, sqlite3_errmsg(*db));
			return -1; // error
		}

		rowid = sqlite3_last_insert_rowid(*db);
		if (rowid == 0){
			fprintf(stderr, "SQL last_insert_rowid failed\n");
			return -1;
		}
		fprintf(stderr, "row ID: %lld\n", rowid);

		rc = insert_tool_rel(data->sql_rel, database->tool_id, rowid);
		if (rc != SQLITE_DONE) {
			fprintf(stderr, "SQL insert tool_rel error: %d: :%s\n", rc, sqlite3_errmsg(*db));
			return -1;
		}

		return 1; // successfully inserted
	} else {
		return 0; // same data already in the database
	}
}

int get_id (sqlite3 *db, char *table, char *column, char* value)
{
	int id = 0;
	int rc = 0;
	char *query = malloc(sizeof(char) * MAX_SQL_STMT_LEN);
	if (query == NULL){
		fprintf(stderr, "Malloc failed\n");
		return id;
	}
	memset(query, 0, MAX_SQL_STMT_LEN);
	sqlite3_stmt *stmt;

	sprintf(query,"SELECT id FROM %s WHERE %s = \"%s\";", table, column, value);

	rc = sqlite3_prepare_v2(db, query, -1, &stmt, NULL);
	free(query);
	if (rc != SQLITE_OK) {
		fprintf(stderr, "SQL error code: %d: %s\n", rc, sqlite3_errmsg(db));
		sqlite3_finalize(stmt);
		return id;
	}

	rc = sqlite3_step(stmt);
	if (rc == SQLITE_ROW) {
		id = sqlite3_column_int(stmt, 0);
	} else {
		fprintf(stderr, "SQL error code: %d: %s\n", rc, sqlite3_errmsg(db));
		fprintf(stderr, "%s not found in the database\n", column);
	}
	sqlite3_finalize(stmt);
	return id;
}

/* without error_subtype */
int check_duplicates(sqlite3_stmt *stmt, int error_type, int project, char *project_version,
		char *loc_file, char *loc_line)
{
	int rc = 0;

	sqlite3_clear_bindings(stmt);
	sqlite3_reset(stmt);

	sqlite3_bind_int(stmt, 1, error_type);
	sqlite3_bind_int(stmt, 2, project);
	sqlite3_bind_text(stmt, 3, project_version, -1, SQLITE_STATIC);
	sqlite3_bind_text(stmt, 4, loc_file, -1, SQLITE_STATIC);
	sqlite3_bind_text(stmt, 5, loc_line, -1, SQLITE_STATIC);

	rc = sqlite3_step(stmt);
	if (rc == SQLITE_ROW) {
		fprintf(stderr, "Entry is already in database\n");
		return 1;
	}
	return 0;
}

/* without error_subtype */
int insert_error(sqlite3_stmt *stmt, int user, int error_type, int project,
		char *project_version, char *loc_file, char *loc_line,
		char *url)
{
	sqlite3_clear_bindings(stmt);
	sqlite3_reset(stmt);
	sqlite3_bind_int(stmt, 1, user);
	sqlite3_bind_int(stmt, 2, error_type);
	sqlite3_bind_int(stmt, 3, project);
	sqlite3_bind_text(stmt, 4, project_version, -1, SQLITE_STATIC);
	sqlite3_bind_text(stmt, 5, loc_file, -1, SQLITE_STATIC);
	sqlite3_bind_text(stmt, 6, loc_line, -1, SQLITE_STATIC);
	sqlite3_bind_text(stmt, 7, url, -1, SQLITE_STATIC);
	return sqlite3_step(stmt);
}

int insert_tool_rel(sqlite3_stmt *stmt, int tool_id, int error_id)
{
	sqlite3_clear_bindings(stmt);
	sqlite3_reset(stmt);
	sqlite3_bind_int(stmt, 1, tool_id);
	sqlite3_bind_int(stmt, 2, error_id);
	return sqlite3_step(stmt);
}

