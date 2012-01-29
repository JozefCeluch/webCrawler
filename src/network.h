#ifndef NETWORK_H_
#define NETWORK_H_
#include <curl/curl.h>
#include "parse.h"

/*
 * Prints CURL error message
 */
void curl_error(CURLcode err);

size_t write_call_back(void *ptr, size_t size, size_t nmemb, void *data);

//size_t header_call_back(void *ptr, size_t size, size_t nmemb, void *data);

/*
 * Initializes and runs CURL
 */
int initialize_curl(CURL *curl, char* url, struct htmlData* chunk,
		char* error_buffer);

#endif /* NETWORK_H_ */
