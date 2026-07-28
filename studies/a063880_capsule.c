/*
 * a063880_capsule.c -- hot-loop companion for the bounded A063880 capsule.
 *
 * It performs two independent full membership scans through a supplied bound:
 *   1. conventional smallest-prime-factor sieve;
 *   2. Euler's linear sieve.
 * Both use exact uint64_t divisor-sum arithmetic.  Their membership booleans
 * must agree at every n.  It then direct-enumerates divisors for every member
 * discovered by the first scan and prints one audit record per member.
 *
 * This program says nothing about the unbounded conjectures.  It is a finite
 * arithmetic checker invoked by studies/a063880_capsule.py.
 */

#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>


#define MAX_CAPSULE_LIMIT 10000000UL


static uint32_t gcd_u32(uint32_t a, uint32_t b) {
    while (b != 0) {
        uint32_t next = a % b;
        a = b;
        b = next;
    }
    return a;
}


static uint32_t *primary_spf(uint32_t limit) {
    uint32_t *spf = malloc(((size_t)limit + 1) * sizeof(*spf));
    if (spf == NULL) return NULL;
    for (uint32_t n = 0; n <= limit; ++n) spf[n] = n;
    for (uint32_t p = 2; p <= limit / p; ++p) {
        if (spf[p] != p) continue;
        for (uint32_t multiple = p * p; multiple <= limit; multiple += p) {
            if (spf[multiple] == multiple) spf[multiple] = p;
        }
    }
    return spf;
}


static int member_from_spf(uint32_t n, const uint32_t *spf) {
    uint64_t sigma = 1;
    uint64_t usigma = 1;
    uint32_t value = n;
    while (value > 1) {
        uint32_t p = spf[value];
        uint64_t power = 1;
        while (value % p == 0) {
            value /= p;
            power *= p;
        }
        sigma *= (power * p - 1) / (p - 1);
        usigma *= power + 1;
    }
    return sigma == 2 * usigma;
}


/* Kept separate from member_from_spf so the independent sieve's factor loop
 * is independently reviewable rather than merely a different sieve feeding
 * the same implementation. */
static int member_from_linear_spf(uint32_t n, const uint32_t *spf) {
    uint64_t total_divisors = 1;
    uint64_t total_unitary_divisors = 1;
    uint32_t remaining = n;
    while (remaining != 1) {
        uint32_t prime = spf[remaining];
        uint64_t prime_power = 1;
        while (remaining % prime == 0) {
            remaining /= prime;
            prime_power *= prime;
        }
        total_divisors *= (prime_power * prime - 1) / (prime - 1);
        total_unitary_divisors *= prime_power + 1;
    }
    return total_divisors == 2 * total_unitary_divisors;
}


static uint32_t *linear_spf(uint32_t limit) {
    uint32_t *spf = calloc((size_t)limit + 1, sizeof(*spf));
    size_t prime_cap = (size_t)limit / 4 + 1024;
    uint32_t *primes = malloc(prime_cap * sizeof(*primes));
    size_t prime_count = 0;
    if (spf == NULL || primes == NULL) {
        free(spf);
        free(primes);
        return NULL;
    }
    for (uint32_t n = 2; n <= limit; ++n) {
        if (spf[n] == 0) {
            if (prime_count == prime_cap) {
                size_t next_cap = prime_cap * 2;
                uint32_t *next = realloc(primes, next_cap * sizeof(*primes));
                if (next == NULL) {
                    free(spf);
                    free(primes);
                    return NULL;
                }
                primes = next;
                prime_cap = next_cap;
            }
            spf[n] = n;
            primes[prime_count++] = n;
        }
        uint32_t least = spf[n];
        for (size_t i = 0; i < prime_count; ++i) {
            uint32_t p = primes[i];
            if (p > limit / n) break;
            uint32_t composite = p * n;
            spf[composite] = p;
            if (p == least) break;
        }
    }
    free(primes);
    return spf;
}


static int direct_audit(uint32_t n, const unsigned char *is_member,
                        uint64_t *sigma_out, uint64_t *usigma_out,
                        int *has_proper_member_divisor_out) {
    uint64_t sigma = 0;
    uint64_t usigma = 0;
    int has_proper = 0;
    for (uint32_t d = 1; d <= n / d; ++d) {
        if (n % d != 0) continue;
        uint32_t mate = n / d;
        uint32_t candidates[2] = {d, mate};
        size_t count = (d == mate) ? 1 : 2;
        for (size_t i = 0; i < count; ++i) {
            uint32_t divisor = candidates[i];
            sigma += divisor;
            if (gcd_u32(divisor, n / divisor) == 1) usigma += divisor;
            if (divisor != n && is_member[divisor]) has_proper = 1;
        }
    }
    *sigma_out = sigma;
    *usigma_out = usigma;
    *has_proper_member_divisor_out = has_proper;
    return sigma == 2 * usigma;
}


int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s LIMIT\n", argv[0]);
        return 64;
    }
    char *end = NULL;
    unsigned long parsed = strtoul(argv[1], &end, 10);
    if (end == argv[1] || *end != '\0' || parsed == 0 || parsed > MAX_CAPSULE_LIMIT) {
        fprintf(stderr, "LIMIT must be in [1, 10000000] for this capsule\n");
        return 64;
    }
    uint32_t limit = (uint32_t)parsed;
    unsigned char *is_member = calloc((size_t)limit + 1, sizeof(*is_member));
    size_t capacity = 32768;
    uint32_t *members = malloc(capacity * sizeof(*members));
    if (is_member == NULL || members == NULL) {
        fprintf(stderr, "allocation failure\n");
        free(is_member);
        free(members);
        return 70;
    }

    uint32_t *spf = primary_spf(limit);
    if (spf == NULL) {
        fprintf(stderr, "primary sieve allocation failure\n");
        free(is_member);
        free(members);
        return 70;
    }
    size_t count = 0;
    for (uint32_t n = 1; n <= limit; ++n) {
        if (!member_from_spf(n, spf)) continue;
        if (count == capacity) {
            capacity *= 2;
            uint32_t *next = realloc(members, capacity * sizeof(*members));
            if (next == NULL) {
                fprintf(stderr, "member-list allocation failure\n");
                free(spf);
                free(is_member);
                free(members);
                return 70;
            }
            members = next;
        }
        members[count++] = n;
        is_member[n] = 1;
    }
    free(spf);

    spf = linear_spf(limit);
    if (spf == NULL) {
        fprintf(stderr, "linear sieve allocation failure\n");
        free(is_member);
        free(members);
        return 70;
    }
    for (uint32_t n = 1; n <= limit; ++n) {
        int independent_member = member_from_linear_spf(n, spf);
        if (independent_member != (is_member[n] != 0)) {
            fprintf(stderr, "scan disagreement at n=%" PRIu32 "\n", n);
            free(spf);
            free(is_member);
            free(members);
            return 65;
        }
    }
    free(spf);

    printf("A063880-CAPSULE/1\n");
    printf("COUNT %zu\n", count);
    for (size_t i = 0; i < count; ++i) {
        uint32_t n = members[i];
        uint64_t sigma = 0;
        uint64_t usigma = 0;
        int has_proper = 0;
        if (!direct_audit(n, is_member, &sigma, &usigma, &has_proper)) {
            fprintf(stderr, "direct audit rejects n=%" PRIu32 "\n", n);
            free(is_member);
            free(members);
            return 65;
        }
        printf("M %" PRIu32 " %" PRIu64 " %" PRIu64 " %d\n", n, sigma, usigma, has_proper);
    }
    printf("END\n");
    free(is_member);
    free(members);
    return 0;
}
