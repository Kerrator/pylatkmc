#include "json_mini.h"

#include <stdlib.h>
#include <string.h>
#include <ctype.h>

/* Find the position right after `"<key>":` (colon). Returns NULL if missing.
 * Skips whitespace between ':' and the value. */
static const char *find_value(const char *buf, size_t len, const char *key)
{
    size_t klen = strlen(key);
    /* pattern we look for: "<key>": */
    /* len_needed = klen + 3 (quotes + colon) */
    if (klen + 3 > len) return NULL;
    for (size_t i = 0; i + klen + 3 <= len; ++i) {
        if (buf[i] != '"') continue;
        if (memcmp(buf + i + 1, key, klen) != 0) continue;
        if (buf[i + 1 + klen] != '"') continue;
        /* skip any whitespace before ':' */
        size_t j = i + 1 + klen + 1;
        while (j < len && (buf[j] == ' ' || buf[j] == '\t')) j++;
        if (j >= len || buf[j] != ':') continue;
        j++;
        while (j < len && (buf[j] == ' ' || buf[j] == '\t')) j++;
        return buf + j;
    }
    return NULL;
}

int json_find_int(const char *buf, size_t len, const char *key, long long *out)
{
    const char *p = find_value(buf, len, key);
    if (!p) return -1;
    char *endp = NULL;
    long long v = strtoll(p, &endp, 10);
    if (endp == p) return -1;
    *out = v;
    return 0;
}

int json_find_double(const char *buf, size_t len, const char *key, double *out)
{
    const char *p = find_value(buf, len, key);
    if (!p) return -1;
    char *endp = NULL;
    double v = strtod(p, &endp);
    if (endp == p) return -1;
    *out = v;
    return 0;
}

int json_find_int_array(const char *buf, size_t len, const char *key,
                        long long *out, size_t n_expected)
{
    const char *p = find_value(buf, len, key);
    if (!p || *p != '[') return -1;
    const char *end = buf + len;
    p++;  /* past '[' */
    for (size_t i = 0; i < n_expected; ++i) {
        while (p < end && isspace((unsigned char)*p)) p++;
        char *endp = NULL;
        long long v = strtoll(p, &endp, 10);
        if (endp == p) return -1;
        out[i] = v;
        p = endp;
        while (p < end && isspace((unsigned char)*p)) p++;
        if (i + 1 < n_expected) {
            if (p >= end || *p != ',') return -1;
            p++;
        }
    }
    while (p < end && isspace((unsigned char)*p)) p++;
    if (p >= end || *p != ']') return -1;
    return 0;
}

int json_find_double_array(const char *buf, size_t len, const char *key,
                           double *out, size_t n_expected)
{
    const char *p = find_value(buf, len, key);
    if (!p || *p != '[') return -1;
    const char *end = buf + len;
    p++;  /* past '[' */
    for (size_t i = 0; i < n_expected; ++i) {
        while (p < end && isspace((unsigned char)*p)) p++;
        char *endp = NULL;
        double v = strtod(p, &endp);
        if (endp == p) return -1;
        out[i] = v;
        p = endp;
        while (p < end && isspace((unsigned char)*p)) p++;
        if (i + 1 < n_expected) {
            if (p >= end || *p != ',') return -1;
            p++;
        }
    }
    while (p < end && isspace((unsigned char)*p)) p++;
    if (p >= end || *p != ']') return -1;
    return 0;
}
