#include "config_reader.h"

#include <ctype.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Minimal INI parser. Supported syntax:
 *   [section]
 *   key = value    # or ; comment
 *   blank lines
 *
 * Keys are stored as section.key (case-sensitive). */

static char *lstrip(char *s) {
    while (*s && isspace((unsigned char)*s)) s++;
    return s;
}
static void rstrip(char *s) {
    size_t n = strlen(s);
    while (n > 0 && isspace((unsigned char)s[n - 1])) s[--n] = 0;
}
static void strip_inline_comment(char *s) {
    for (char *p = s; *p; ++p) {
        if (*p == '#' || *p == ';') { *p = 0; return; }
    }
}

static int set_key(InputConfig *cfg, const char *section, const char *key, const char *val)
{
    char qual[128];
    int n = snprintf(qual, sizeof qual, "%s.%s", section, key);
    if (n < 0 || n >= (int)sizeof qual) return -EINVAL;

    if (strcmp(qual, "run.max_steps")       == 0) cfg->max_steps       = strtoull(val, NULL, 10);
    else if (strcmp(qual, "run.max_time_s") == 0) cfg->max_time_s      = strtod(val, NULL);
    else if (strcmp(qual, "run.sample_every")  == 0) cfg->sample_every  = strtoull(val, NULL, 10);
    else if (strcmp(qual, "run.summary_every") == 0) cfg->summary_every = strtoull(val, NULL, 10);
    else if (strcmp(qual, "run.base_seed")     == 0) cfg->base_seed     = strtoull(val, NULL, 10);
    else if (strcmp(qual, "paths.ratetable_path")  == 0)
        snprintf(cfg->ratetable_path,  sizeof cfg->ratetable_path,  "%s", val);
    else if (strcmp(qual, "paths.initconfig_path") == 0)
        snprintf(cfg->initconfig_path, sizeof cfg->initconfig_path, "%s", val);
    else if (strcmp(qual, "paths.output_root") == 0)
        snprintf(cfg->output_root,     sizeof cfg->output_root,     "%s", val);
    else if (strcmp(qual, "physics.temperature_K") == 0) cfg->temperature_K = strtod(val, NULL);
    else if (strcmp(qual, "validation.rng_replay_path") == 0)
        snprintf(cfg->rng_replay_path, sizeof cfg->rng_replay_path, "%s", val);
    else {
        fprintf(stderr, "input_config_load: unknown key '%s'\n", qual);
        /* Non-fatal; unknown keys are ignored. */
    }
    return 0;
}

/* If path is non-empty and relative (no leading '/'), prepend dir.
 * Strips a leading "./" from path before joining so "foo/./bar" doesn't appear
 * in printed diagnostics. */
static void resolve_relative(char *path, size_t cap, const char *dir)
{
    if (!path || !*path || !dir || !*dir) return;
    if (path[0] == '/') return;
    const char *p = path;
    while (p[0] == '.' && p[1] == '/') p += 2;
    char tmp[1024];
    int n = snprintf(tmp, sizeof tmp, "%s/%s", dir, p);
    if (n < 0 || n >= (int)sizeof tmp) return;
    snprintf(path, cap, "%s", tmp);
}

int input_config_load(InputConfig *out, const char *path)
{
    if (!out || !path) return -EINVAL;
    memset(out, 0, sizeof(*out));

    /* Defaults. */
    out->max_steps       = 1000000ULL;
    out->max_time_s      = 0.0;
    out->sample_every    = 1000ULL;
    out->summary_every   = 0ULL;
    out->base_seed       = 42ULL;
    out->temperature_K   = 500.0;
    snprintf(out->output_root, sizeof out->output_root, "%s", "./output");

    FILE *fp = fopen(path, "r");
    if (!fp) {
        fprintf(stderr, "input_config_load: open(%s): %s\n", path, strerror(errno));
        return -errno;
    }

    char section[64] = {0};
    char line[1024];
    int  lineno = 0;
    while (fgets(line, sizeof line, fp)) {
        lineno++;
        strip_inline_comment(line);
        char *s = lstrip(line);
        rstrip(s);
        if (*s == 0) continue;

        if (*s == '[') {
            char *end = strchr(s, ']');
            if (!end) { fclose(fp); return -EPROTO; }
            *end = 0;
            snprintf(section, sizeof section, "%s", s + 1);
            continue;
        }

        char *eq = strchr(s, '=');
        if (!eq) {
            fprintf(stderr, "input_config_load: %s:%d missing '=': '%s'\n",
                    path, lineno, s);
            continue;
        }
        *eq = 0;
        char *key = s;       rstrip(key);
        char *val = eq + 1;  val = lstrip(val); rstrip(val);
        set_key(out, section, key, val);
    }
    fclose(fp);

    /* Resolve relative paths against the input file's directory. */
    char ini_dir[512];
    snprintf(ini_dir, sizeof ini_dir, "%s", path);
    char *slash = strrchr(ini_dir, '/');
    if (slash) *slash = 0;
    else snprintf(ini_dir, sizeof ini_dir, "%s", ".");
    resolve_relative(out->ratetable_path,  sizeof out->ratetable_path,  ini_dir);
    resolve_relative(out->initconfig_path, sizeof out->initconfig_path, ini_dir);
    resolve_relative(out->output_root,     sizeof out->output_root,     ini_dir);
    resolve_relative(out->rng_replay_path, sizeof out->rng_replay_path, ini_dir);

    return 0;
}
