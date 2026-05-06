#include "rng.h"

static inline uint64_t rotl(uint64_t x, int k) {
    return (x << k) | (x >> (64 - k));
}

static uint64_t splitmix64(uint64_t *x) {
    uint64_t z = (*x += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

void rng_seed(Rng *rng, uint64_t base_seed, uint32_t rank) {
    uint64_t seed = base_seed ^ ((uint64_t)rank * 0xda3e39cb94b95bdbULL);
    rng->s[0] = splitmix64(&seed);
    rng->s[1] = splitmix64(&seed);
    rng->s[2] = splitmix64(&seed);
    rng->s[3] = splitmix64(&seed);
    /* Guard against the all-zero state (never produced by splitmix64, but
     * documented safety check for xoshiro256++). */
    if ((rng->s[0] | rng->s[1] | rng->s[2] | rng->s[3]) == 0) {
        rng->s[0] = 1;
    }
}

uint64_t rng_next_u64(Rng *rng) {
    const uint64_t result = rotl(rng->s[0] + rng->s[3], 23) + rng->s[0];
    const uint64_t t      = rng->s[1] << 17;
    rng->s[2] ^= rng->s[0];
    rng->s[3] ^= rng->s[1];
    rng->s[1] ^= rng->s[2];
    rng->s[0] ^= rng->s[3];
    rng->s[2] ^= t;
    rng->s[3]  = rotl(rng->s[3], 45);
    return result;
}

double rng_next_double(Rng *rng) {
    /* 53-bit mantissa, same convention as std::generate_canonical. */
    return (rng_next_u64(rng) >> 11) * (1.0 / (double)(1ULL << 53));
}

void rng_next2(Rng *rng, double *r1, double *r2) {
    *r1 = rng_next_double(rng);
    *r2 = rng_next_double(rng);
}
