#include "kmcfmt.h"

#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

static uint32_t read_u32_le(const void *p) {
    const unsigned char *b = (const unsigned char *)p;
    return  (uint32_t)b[0]        |
           ((uint32_t)b[1] <<  8) |
           ((uint32_t)b[2] << 16) |
           ((uint32_t)b[3] << 24);
}

int kmcfmt_mmap(KmcMap *out, const char *path, const char *expected_magic)
{
    if (!out || !path || !expected_magic) return -EINVAL;
    memset(out, 0, sizeof(*out));

    int fd = open(path, O_RDONLY);
    if (fd < 0) {
        fprintf(stderr, "kmcfmt: open(%s): %s\n", path, strerror(errno));
        return -errno;
    }
    struct stat st;
    if (fstat(fd, &st) != 0) {
        int e = errno; close(fd); return -e;
    }
    if ((size_t)st.st_size < 8 + 4) {
        close(fd); return -EPROTO;
    }

    void *base = mmap(NULL, (size_t)st.st_size, PROT_READ, MAP_PRIVATE, fd, 0);
    close(fd);
    if (base == MAP_FAILED) {
        fprintf(stderr, "kmcfmt: mmap(%s): %s\n", path, strerror(errno));
        return -errno;
    }

    const unsigned char *p = (const unsigned char *)base;
    if (memcmp(p, expected_magic, 8) != 0) {
        fprintf(stderr, "kmcfmt: bad magic in %s (expected \"%.8s\")\n",
                path, expected_magic);
        munmap(base, (size_t)st.st_size);
        return -EPROTO;
    }
    uint32_t header_bytes = read_u32_le(p + 8);
    size_t   header_off   = 12;
    size_t   payload_off  = header_off + header_bytes;
    if (payload_off > (size_t)st.st_size) {
        munmap(base, (size_t)st.st_size);
        return -EPROTO;
    }

    out->base        = base;
    out->size        = (size_t)st.st_size;
    out->header      = (const char *)(p + header_off);
    out->header_len  = header_bytes;
    out->payload     = (const void *)(p + payload_off);
    out->payload_len = (size_t)st.st_size - payload_off;
    return 0;
}

void kmcfmt_unmap(KmcMap *m)
{
    if (!m || !m->base) return;
    munmap(m->base, m->size);
    memset(m, 0, sizeof(*m));
}
