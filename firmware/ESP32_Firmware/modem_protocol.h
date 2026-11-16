#pragma once
#include <ctype.h>
#include <stdio.h>
#include <string.h>

namespace IotProtocol {

// Build a URL without carrying editor whitespace into the modem's URL field.
inline bool joinUrl(const char* base, const char* path, char* output, size_t capacity) {
  if (!output || !capacity) return false;
  output[0] = '\0';
  if (!base || !path) return false;
  while (*base && isspace(static_cast<unsigned char>(*base))) ++base;
  size_t baseLength = strlen(base);
  while (baseLength && isspace(static_cast<unsigned char>(base[baseLength - 1]))) --baseLength;
  while (baseLength && base[baseLength - 1] == '/') --baseLength;
  if (baseLength <= 8 || strncmp(base, "https://", 8) != 0) return false;
  for (size_t i = 0; i < baseLength; ++i) {
    if (isspace(static_cast<unsigned char>(base[i])) || base[i] == '"') return false;
  }
  while (*path && isspace(static_cast<unsigned char>(*path))) ++path;
  size_t pathLength = strlen(path);
  while (pathLength && isspace(static_cast<unsigned char>(path[pathLength - 1]))) --pathLength;
  while (pathLength && *path == '/') { ++path; --pathLength; }
  for (size_t i = 0; i < pathLength; ++i) {
    if (isspace(static_cast<unsigned char>(path[i])) || path[i] == '"') return false;
  }
  if (baseLength + 1 + pathLength + 1 > capacity) return false;
  memcpy(output, base, baseLength);
  output[baseLength] = '/';
  memcpy(output + baseLength + 1, path, pathLength);
  output[baseLength + 1 + pathLength] = '\0';
  return true;
}

inline bool containsCompleteLine(const char* response, const char* token) {
  if (!response || !token || !*token) return false;
  const char* match = strstr(response, token);
  return match && strchr(match + strlen(token), '\n');
}

// A UART read may stop halfway through "+HTTPACTION: 1,200,12".
inline int parseHttpAction(const char* response, int expectedMethod) {
  if (!response) return -1;
  const char* cursor = response;
  while ((cursor = strstr(cursor, "+HTTPACTION:"))) {
    const char* end = strchr(cursor, '\n');
    if (!end) return -1;
    size_t length = static_cast<size_t>(end - cursor);
    if (length < 96) {
      char line[96];
      memcpy(line, cursor, length);
      line[length] = '\0';
      int method = -1, status = -1, used = 0;
      long bodyLength = -1;
      if (sscanf(line, "+HTTPACTION: %d , %d , %ld %n",
                 &method, &status, &bodyLength, &used) == 3
          && used > 0 && line[used] == '\0'
          && method == expectedMethod && status >= 0 && status <= 999 && bodyLength >= 0) {
        return status;
      }
    }
    cursor = end + 1;
  }
  return -1;
}
}
