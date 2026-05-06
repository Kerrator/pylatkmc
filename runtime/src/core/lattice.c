#include "lattice.h"

#include <errno.h>
#include <stdlib.h>
#include <sys/mman.h>

/* Lattice is populated by initconfig_load via a shared mmap. The mmap is
 * owned here; freeing releases it and clears all aliasing pointers. */

int lattice_load_kmcinit(Lattice *out, const char *path)
{
    /* Preserved for completeness; the main path is initconfig_load which also
     * populates a State. Delegating directly would force a dummy State, so we
     * leave this unimplemented for now. */
    (void)out; (void)path;
    return -ENOSYS;
}

void lattice_free(Lattice *l)
{
    if (!l) return;
    if (l->_mmap_base) {
        munmap(l->_mmap_base, l->_mmap_size);
    }
    l->_mmap_base    = NULL;
    l->_mmap_size    = 0;
    l->positions     = NULL;
    l->layer_index   = NULL;
    l->site_class    = NULL;
    l->nn1_offsets   = NULL;
    l->nn1_indices   = NULL;
    l->nn1_dir_family = NULL;
    l->nn2_offsets   = NULL;
    l->nn2_indices   = NULL;
    l->nn2_dir_family = NULL;
    l->n_sites = 0;
    l->n_layers = 0;
}
