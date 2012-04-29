/*! \file network.h
    \brief Part of program regarding network communication.

    Contains definitions of structures and functions that download
    data from the Internet.
*/
#ifndef NETWORK_H_
#define NETWORK_H_
#include <curl/curl.h>
#include "parse.h"

/*! \fn void curl_error(CURLcode err)
    \brief Prints CURL error message.
    \param err Error number.
*/
void curl_error(CURLcode err);

/*! \fn size_t write_call_back(void *ptr, size_t size, size_t nmemb, void *data)
    \brief Callback function used by CURL library.
    \param ptr
    \param size
    \param nmemb
    \param data
    \return Written size
*/
size_t write_call_back(void *ptr, size_t size, size_t nmemb, void *data);

//size_t header_call_back(void *ptr, size_t size, size_t nmemb, void *data);

/*! \fn int initialize_curl(CURL *curl, char* url, struct htmlData* chunk, char* error_buffer);
    \brief Initializes and runs CURL
    \param curl Uninitialized CURL structure
    \param url Buffer with url address
    \param chunk Structure containing data downloaded by curl
    \param error_buffer CURL error buffer
    \return 0 OK
    \return -1 Curl init error
    \return -2 Connection error
 */
int initialize_curl(CURL *curl, char* url, struct htmlData* chunk,
		char* error_buffer, char* post);

#endif /* NETWORK_H_ */
