#include "network.h"

void curl_error(CURLcode err)
{
	const char *error_msg;
	if (err) {
		error_msg = curl_easy_strerror(err);
		fprintf(stderr, "%s\n", error_msg);
	}
}

size_t write_call_back(void *ptr, size_t size, size_t nmemb, void *data)
{
	int real_size = size * nmemb;
	struct htmlData *memory = (struct htmlData *) data;
	memory->page = (char *) realloc(memory->page, memory->size + real_size
			+ 1);

	if (memory->page) {
		memcpy(&(memory->page[memory->size]), ptr, real_size);
		memory->size += real_size;
		memory->page[memory->size] = '\0';
	}
	return real_size;
}

//size_t header_call_back(void *ptr, size_t size, size_t nmemb, void *data)
//{
//	int real_size = size * nmemb;
//	struct htmlData *memory = (struct htmlData *) data;
//
//	memory->data = (char *) realloc(memory->data, memory->size + real_size
//			+ 1);
//	if (memory->data) {
//		memcpy(&(memory->data[memory->size]), ptr, real_size);
//		memory->size += real_size;
//		memory->data[memory->size] = '\0';
//	}
//	return real_size;
//}

int initialize_curl(CURL *curl, char* url, struct htmlData* chunk,
		char* error_buffer)
{
	long response_code = 0;
	CURLcode err;
//	double content_size = 0;

	curl = curl_easy_init();

	if (curl) {
		err = curl_easy_setopt(curl, CURLOPT_URL, url);
		curl_error(err);
		err = curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1);
		curl_error(err);
		err = curl_easy_setopt(curl, CURLOPT_USERAGENT, "httpConnect");
		curl_error(err);
		err = curl_easy_setopt(curl, CURLOPT_ERRORBUFFER, error_buffer);
		curl_error(err);
		err = curl_easy_setopt(curl, CURLOPT_CAPATH, "/etc/ssl/certs");
		curl_error(err);
		err = curl_easy_setopt(curl, CURLOPT_SSL_VERIFYHOST, 2L);
		curl_error(err);
		err = curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 0);
		curl_error(err);
		err = curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_call_back);
		curl_error(err);
		err = curl_easy_setopt(curl, CURLOPT_WRITEDATA, (void *)chunk);
		curl_error(err);
		err = curl_easy_setopt(curl, CURLOPT_MAXREDIRS, 0L); // 0 = no redirs
		curl_error(err);
//		curl_error(curl_easy_setopt(curl, CURLOPT_VERBOSE, 1)); // info about curl operations
		curl_error(curl_easy_perform(curl));

		curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &response_code);
//		curl_easy_getinfo(curl, CURLINFO_CONTENT_LENGTH_DOWNLOAD, &content_size);

		curl_easy_cleanup(curl);

		if (response_code == 200) {
			printf("Download OK\n");
			return 0;
		} else {
			printf("Page not downloaded, status code: %ld\n",
					response_code);
			printf("%s\n", error_buffer);
			return 1;
		}
	}
	printf("Curl init error\n");
	curl_easy_cleanup(curl);
	return 1;
}

