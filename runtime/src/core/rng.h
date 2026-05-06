#ifndef LATKMC_RNG_H
#define LATKMC_RNG_H

#include <stdint.h>

/* xoshiro256++ state, seeded via splitmix64 from (base_seed, rank).
 * Reproducible across runs with the same (base_seed, rank) pair. */
typedef struct {
    uint64_t s[4];
} Rng;

/* Seed from a base seed XOR'd with the rank id, expanded via splitmix64. */
void    rng_seed(Rng *rng, uint64_t base_seed, uint32_t rank);

uint64_t rng_next_u64(Rng *rng);

/* Uniform double in [0, 1). */
double   rng_next_double(Rng *rng);

/* Two uniform doubles in [0, 1), drawn in a fixed order (r1, r2).
 * r1 is the event-selection draw, r2 is the time-increment draw. */
void     rng_next2(Rng *rng, double *r1, double *r2);

#endif /* LATKMC_RNG_H */
