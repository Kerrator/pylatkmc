#ifndef LATKMC_KMCFMT_H
#define LATKMC_KMCFMT_H

/* Shared mmap + header-validation helpers for .kmcrt and .kmcinit files.
 * Both formats share:
 *     u8[8]   magic
 *     u32     header_bytes         (little-endian)
 *     u8[H]   JSON header (4-byte aligned including trailing NULs)
 *     ...     format-specific payload
 */

#include <stddef.h>

typedef struct {
    void       *base;       /* mmap base, PROT_READ */
    size_t      size;       /* mmap length */
    const char *header;     /* pointer into base to the JSON header */
    size_t      header_len;
    const void *payload;    /* pointer into base to the start of the payload */
    size_t      payload_len;
} KmcMap;

/* Open, mmap, validate magic, locate header + payload. Caller eventually frees
 * with kmcfmt_unmap(). Returns 0 on success, -errno on failure. */
int  kmcfmt_mmap(KmcMap *out, const char *path, const char *expected_magic);
void kmcfmt_unmap(KmcMap *m);

#endif /* LATKMC_KMCFMT_H */
