#ifndef LATKMC_JSON_MINI_H
#define LATKMC_JSON_MINI_H

/* Tiny JSON extractor for the kmcfmt headers. NOT a general-purpose parser.
 *
 * Only supports the shapes we emit from tools/kmcfmt.py:
 *   "key":<number>
 *   "key":"<string>"
 *   "key":[<number>, <number>, ...]
 *
 * All functions search for the literal  "<key>":  and parse what follows.
 * Returns 0 on success, -1 on "not found / shape mismatch". */

#include <stddef.h>

int json_find_int   (const char *buf, size_t len, const char *key, long long *out);
int json_find_double(const char *buf, size_t len, const char *key, double *out);
int json_find_int_array(const char *buf, size_t len, const char *key,
                        long long *out, size_t n_expected);
int json_find_double_array(const char *buf, size_t len, const char *key,
                           double *out, size_t n_expected);

#endif /* LATKMC_JSON_MINI_H */
