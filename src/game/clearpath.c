/*
 *  This file is part of Permafrost Engine. 
 *  Copyright (C) 2019-2023 Eduard Permyakov 
 *
 *  Permafrost Engine is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  Permafrost Engine is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program.  If not, see <http://www.gnu.org/licenses/>.
 * 
 *  Linking this software statically or dynamically with other modules is making 
 *  a combined work based on this software. Thus, the terms and conditions of 
 *  the GNU General Public License cover the whole combination. 
 *  
 *  As a special exception, the copyright holders of Permafrost Engine give 
 *  you permission to link Permafrost Engine with independent modules to produce 
 *  an executable, regardless of the license terms of these independent 
 *  modules, and to copy and distribute the resulting executable under 
 *  terms of your choice, provided that you also meet, for each linked 
 *  independent module, the terms and conditions of the license of that 
 *  module. An independent module is a module which is not derived from 
 *  or based on Permafrost Engine. If you modify Permafrost Engine, you may 
 *  extend this exception to your version of Permafrost Engine, but you are not 
 *  obliged to do so. If you do not wish to do so, delete this exception 
 *  statement from your version.
 *
 */

/* References:
 *     [1] ClearPath: Highly Parallel Collision Avoidance for
 *         Multi-Agent Simulation
 *         (http://gamma.cs.unc.edu/CA/ClearPath.pdf)
 *     [2] The Hybrid Reciprocal Velocity Obstacle
 *         (http://gamma.cs.unc.edu/HRVO/HRVO-T-RO.pdf)
 */

#include "clearpath.h"
#include "public/game.h"
#include "movement.h"
#include "game_private.h"
#include "../main.h"
#include "../event.h"
#include "../entity.h"
#include "../settings.h"
#include "../ui.h"
#include "../perf.h"
#include "../phys/public/collision.h"
#include "../render/public/render.h"
#include "../render/public/render_ctrl.h"
#include "../map/public/map.h"
#include "../lib/public/pf_string.h"
#include "../lib/public/mem.h"

#include <assert.h>
#include <SDL.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>


#define EPSILON         (1.0/1024)
#define EPSILON_SQ      (EPSILON * EPSILON)
#define MAX_SAVED_VOS   (512)

VEC_TYPE(vec2, vec2_t)
VEC_IMPL(static inline, vec2, vec2_t)

struct VO{
    vec2_t xz_apex;
    vec2_t xz_left_side;
    vec2_t xz_right_side;
};

struct RVO{
    vec2_t xz_apex;
    vec2_t xz_left_side;
    vec2_t xz_right_side;
};

struct HRVO{
    vec2_t xz_apex;
    vec2_t xz_left_side;
    vec2_t xz_right_side;
};

struct saved_ctx{
    struct cp_ent cpent;
    vec2_t        ent_des_v;
    struct HRVO   hrvos[MAX_SAVED_VOS];
    struct VO     vos[MAX_SAVED_VOS];
    size_t        n_hrvos;
    size_t        n_vos;
    vec2_t        v_new;
    vec_vec2_t    xpoints;
    bool          des_v_in_pcr;
    bool          valid;
};

enum clearpath_timing_stage{
    CLEARPATH_TIMING_CONSTRAINT_CAP,
    CLEARPATH_TIMING_ATTEMPT_SETUP,
    CLEARPATH_TIMING_DESIRED_PCR,
    CLEARPATH_TIMING_INSIDE_PCR,
    CLEARPATH_TIMING_XPOINTS,
    CLEARPATH_TIMING_PROJECTION,
    CLEARPATH_TIMING_COMPUTE_VNEW,
    CLEARPATH_TIMING_FALLBACK_REMOVE,
    CLEARPATH_TIMING_STAGE_COUNT
};

struct clearpath_stage_stats{
    uint64_t count;
    uint64_t total_us;
    uint64_t max_us;
};

struct clearpath_stats{
    bool enabled;
    const char *path;

    uint64_t calls;
    uint64_t attempts;
    uint64_t successes;
    uint64_t zero_velocity_returns;
    uint64_t fallback_retry_steps;
    uint64_t fallback_removes;
    uint64_t fallback_cap_returns;
    uint64_t constraint_cap_attempts;
    uint64_t constraint_cap_removes;
    uint64_t constraint_cap_max_input_neighbours;

    uint64_t dynamic_neighbours;
    uint64_t static_neighbours;
    uint64_t hrvos;
    uint64_t vos;
    uint64_t rays;
    uint64_t max_rays;

    uint64_t desired_outside_pcr;
    uint64_t desired_inside_pcr;

    uint64_t inside_pcr_calls;
    uint64_t inside_pcr_ray_pair_tests;
    uint64_t inside_pcr_hits;
    uint64_t inside_pcr_misses;
    uint64_t inside_pcr_apex_skips;

    uint64_t xpoint_calls;
    uint64_t xpoint_ray_pair_tests;
    uint64_t xpoint_ray_pair_intersections;
    uint64_t xpoint_inside_rejected;
    uint64_t xpoint_accepted;

    uint64_t projection_calls;
    uint64_t projection_tests;
    uint64_t projection_accepted;

    uint64_t candidate_points_total;
    uint64_t max_candidate_points;
    uint64_t no_solution_attempts;
    struct clearpath_stage_stats stages[CLEARPATH_TIMING_STAGE_COUNT];
};

/*****************************************************************************/
/* STATIC VARIABLES                                                          */
/*****************************************************************************/

static struct saved_ctx s_debug_saved;
static struct clearpath_stats s_clearpath_stats;
static size_t s_fallback_remove_batch = 4;
static size_t s_fallback_batch_min_neighbs = 40;
static size_t s_fallback_max_removes;
static size_t s_max_constraint_neighbs = 32;

static const char *s_clearpath_stage_str[] = {
    [CLEARPATH_TIMING_CONSTRAINT_CAP]   = "constraint_cap",
    [CLEARPATH_TIMING_ATTEMPT_SETUP]    = "attempt_setup",
    [CLEARPATH_TIMING_DESIRED_PCR]      = "desired_pcr",
    [CLEARPATH_TIMING_INSIDE_PCR]       = "inside_pcr",
    [CLEARPATH_TIMING_XPOINTS]          = "xpoints",
    [CLEARPATH_TIMING_PROJECTION]       = "projection",
    [CLEARPATH_TIMING_COMPUTE_VNEW]     = "compute_vnew",
    [CLEARPATH_TIMING_FALLBACK_REMOVE]  = "fallback_remove"
};

/*****************************************************************************/
/* STATIC FUNCTIONS                                                          */
/*****************************************************************************/

static size_t clearpath_parse_size_env(const char *name, size_t fallback)
{
    const char *value = getenv(name);
    if(!value || !value[0])
        return fallback;

    char *end = NULL;
    unsigned long parsed = strtoul(value, &end, 10);
    if(end == value)
        return fallback;

    return (size_t)parsed;
}

static void clearpath_config_init(void)
{
    s_fallback_remove_batch = clearpath_parse_size_env(
        "PF_CLEARPATH_FALLBACK_REMOVE_BATCH", 4);
    if(s_fallback_remove_batch == 0)
        s_fallback_remove_batch = 1;

    s_fallback_batch_min_neighbs = clearpath_parse_size_env(
        "PF_CLEARPATH_FALLBACK_BATCH_MIN_NEIGHBOURS", 40);
    s_fallback_max_removes = clearpath_parse_size_env(
        "PF_CLEARPATH_FALLBACK_MAX_REMOVES", 0);
    s_max_constraint_neighbs = clearpath_parse_size_env(
        "PF_CLEARPATH_MAX_CONSTRAINT_NEIGHBOURS", 32);
}

static inline void clearpath_stats_add_impl(uint64_t *field, uint64_t value)
{
    __sync_fetch_and_add(field, value);
}

static inline void clearpath_stats_max_impl(uint64_t *field, uint64_t value)
{
    uint64_t curr;
    do{
        curr = __sync_fetch_and_add(field, 0);
        if(curr >= value)
            return;
    }while(!__sync_bool_compare_and_swap(field, curr, value));
}

#define clearpath_stats_add(field, value) \
    do { \
        uint64_t stats_value__ = (uint64_t)(value); \
        if(s_clearpath_stats.enabled && stats_value__ != 0) \
            clearpath_stats_add_impl((field), stats_value__); \
    } while(0)

#define clearpath_stats_max(field, value) \
    do { \
        if(s_clearpath_stats.enabled) \
            clearpath_stats_max_impl((field), (uint64_t)(value)); \
    } while(0)

static double clearpath_stats_avg(uint64_t total, uint64_t count)
{
    return count ? (double)total / (double)count : 0.0;
}

static uint64_t clearpath_timing_begin(void)
{
    if(!s_clearpath_stats.enabled)
        return 0;
    return SDL_GetPerformanceCounter();
}

static uint64_t clearpath_timing_elapsed_us(uint64_t begin)
{
    uint64_t elapsed = SDL_GetPerformanceCounter() - begin;
    uint64_t freq = SDL_GetPerformanceFrequency();
    if(freq == 0)
        return 0;
    return (elapsed * 1000000ull) / freq;
}

static void clearpath_stats_timing(enum clearpath_timing_stage stage, uint64_t begin)
{
    if(!s_clearpath_stats.enabled || begin == 0)
        return;

    uint64_t elapsed_us = clearpath_timing_elapsed_us(begin);
    struct clearpath_stage_stats *stats = &s_clearpath_stats.stages[stage];
    clearpath_stats_add_impl(&stats->count, 1);
    clearpath_stats_add_impl(&stats->total_us, elapsed_us);
    clearpath_stats_max_impl(&stats->max_us, elapsed_us);
}

static void clearpath_stats_init(void)
{
    memset(&s_clearpath_stats, 0, sizeof(s_clearpath_stats));

    const char *path = getenv("PF_CLEARPATH_STATS_PATH");
    if(path && path[0]) {
        s_clearpath_stats.enabled = true;
        s_clearpath_stats.path = path;
    }
}

static void clearpath_stats_write(void)
{
    if(!s_clearpath_stats.enabled || !s_clearpath_stats.path)
        return;

    FILE *fp = fopen(s_clearpath_stats.path, "w");
    if(!fp) {
        fprintf(stderr, "PF_CLEARPATH_STATS_PATH failed to open: %s\n",
            s_clearpath_stats.path);
        return;
    }

    fprintf(fp, "{\n");
    fprintf(fp, "  \"calls\": %llu,\n", (unsigned long long)s_clearpath_stats.calls);
    fprintf(fp, "  \"attempts\": %llu,\n", (unsigned long long)s_clearpath_stats.attempts);
    fprintf(fp, "  \"successes\": %llu,\n", (unsigned long long)s_clearpath_stats.successes);
    fprintf(fp, "  \"zero_velocity_returns\": %llu,\n", (unsigned long long)s_clearpath_stats.zero_velocity_returns);
    fprintf(fp, "  \"fallback_remove_batch\": %llu,\n", (unsigned long long)s_fallback_remove_batch);
    fprintf(fp, "  \"fallback_batch_min_neighbours\": %llu,\n", (unsigned long long)s_fallback_batch_min_neighbs);
    fprintf(fp, "  \"fallback_max_removes\": %llu,\n", (unsigned long long)s_fallback_max_removes);
    fprintf(fp, "  \"max_constraint_neighbours\": %llu,\n", (unsigned long long)s_max_constraint_neighbs);
    fprintf(fp, "  \"fallback_retry_steps\": %llu,\n", (unsigned long long)s_clearpath_stats.fallback_retry_steps);
    fprintf(fp, "  \"fallback_removes\": %llu,\n", (unsigned long long)s_clearpath_stats.fallback_removes);
    fprintf(fp, "  \"fallback_cap_returns\": %llu,\n", (unsigned long long)s_clearpath_stats.fallback_cap_returns);
    fprintf(fp, "  \"constraint_cap_attempts\": %llu,\n", (unsigned long long)s_clearpath_stats.constraint_cap_attempts);
    fprintf(fp, "  \"constraint_cap_removes\": %llu,\n", (unsigned long long)s_clearpath_stats.constraint_cap_removes);
    fprintf(fp, "  \"constraint_cap_max_input_neighbours\": %llu,\n", (unsigned long long)s_clearpath_stats.constraint_cap_max_input_neighbours);
    fprintf(fp, "  \"dynamic_neighbours\": %llu,\n", (unsigned long long)s_clearpath_stats.dynamic_neighbours);
    fprintf(fp, "  \"static_neighbours\": %llu,\n", (unsigned long long)s_clearpath_stats.static_neighbours);
    fprintf(fp, "  \"hrvos\": %llu,\n", (unsigned long long)s_clearpath_stats.hrvos);
    fprintf(fp, "  \"vos\": %llu,\n", (unsigned long long)s_clearpath_stats.vos);
    fprintf(fp, "  \"rays\": %llu,\n", (unsigned long long)s_clearpath_stats.rays);
    fprintf(fp, "  \"max_rays\": %llu,\n", (unsigned long long)s_clearpath_stats.max_rays);
    fprintf(fp, "  \"desired_outside_pcr\": %llu,\n", (unsigned long long)s_clearpath_stats.desired_outside_pcr);
    fprintf(fp, "  \"desired_inside_pcr\": %llu,\n", (unsigned long long)s_clearpath_stats.desired_inside_pcr);
    fprintf(fp, "  \"inside_pcr_calls\": %llu,\n", (unsigned long long)s_clearpath_stats.inside_pcr_calls);
    fprintf(fp, "  \"inside_pcr_ray_pair_tests\": %llu,\n", (unsigned long long)s_clearpath_stats.inside_pcr_ray_pair_tests);
    fprintf(fp, "  \"inside_pcr_hits\": %llu,\n", (unsigned long long)s_clearpath_stats.inside_pcr_hits);
    fprintf(fp, "  \"inside_pcr_misses\": %llu,\n", (unsigned long long)s_clearpath_stats.inside_pcr_misses);
    fprintf(fp, "  \"inside_pcr_apex_skips\": %llu,\n", (unsigned long long)s_clearpath_stats.inside_pcr_apex_skips);
    fprintf(fp, "  \"xpoint_calls\": %llu,\n", (unsigned long long)s_clearpath_stats.xpoint_calls);
    fprintf(fp, "  \"xpoint_ray_pair_tests\": %llu,\n", (unsigned long long)s_clearpath_stats.xpoint_ray_pair_tests);
    fprintf(fp, "  \"xpoint_ray_pair_intersections\": %llu,\n", (unsigned long long)s_clearpath_stats.xpoint_ray_pair_intersections);
    fprintf(fp, "  \"xpoint_inside_rejected\": %llu,\n", (unsigned long long)s_clearpath_stats.xpoint_inside_rejected);
    fprintf(fp, "  \"xpoint_accepted\": %llu,\n", (unsigned long long)s_clearpath_stats.xpoint_accepted);
    fprintf(fp, "  \"projection_calls\": %llu,\n", (unsigned long long)s_clearpath_stats.projection_calls);
    fprintf(fp, "  \"projection_tests\": %llu,\n", (unsigned long long)s_clearpath_stats.projection_tests);
    fprintf(fp, "  \"projection_accepted\": %llu,\n", (unsigned long long)s_clearpath_stats.projection_accepted);
    fprintf(fp, "  \"candidate_points_total\": %llu,\n", (unsigned long long)s_clearpath_stats.candidate_points_total);
    fprintf(fp, "  \"max_candidate_points\": %llu,\n", (unsigned long long)s_clearpath_stats.max_candidate_points);
    fprintf(fp, "  \"no_solution_attempts\": %llu,\n", (unsigned long long)s_clearpath_stats.no_solution_attempts);
    fprintf(fp, "  \"stage_timings\": {\n");
    for(int i = 0; i < CLEARPATH_TIMING_STAGE_COUNT; i++) {
        struct clearpath_stage_stats *stats = &s_clearpath_stats.stages[i];
        double avg_ms = (stats->count > 0)
            ? ((double)stats->total_us / 1000.0) / (double)stats->count
            : 0.0;
        fprintf(fp, "    \"%s\": {\n", s_clearpath_stage_str[i]);
        fprintf(fp, "      \"count\": %llu,\n", (unsigned long long)stats->count);
        fprintf(fp, "      \"total_ms\": %.6f,\n", (double)stats->total_us / 1000.0);
        fprintf(fp, "      \"avg_ms\": %.6f,\n", avg_ms);
        fprintf(fp, "      \"max_ms\": %.6f\n", (double)stats->max_us / 1000.0);
        fprintf(fp, "    }%s\n", (i == CLEARPATH_TIMING_STAGE_COUNT - 1) ? "" : ",");
    }
    fprintf(fp, "  },\n");
    fprintf(fp, "  \"avg_rays_per_attempt\": %.6f,\n",
        clearpath_stats_avg(s_clearpath_stats.rays, s_clearpath_stats.attempts));
    fprintf(fp, "  \"avg_inside_pair_tests_per_call\": %.6f,\n",
        clearpath_stats_avg(s_clearpath_stats.inside_pcr_ray_pair_tests,
            s_clearpath_stats.inside_pcr_calls));
    fprintf(fp, "  \"avg_xpoint_pair_tests_per_call\": %.6f,\n",
        clearpath_stats_avg(s_clearpath_stats.xpoint_ray_pair_tests,
            s_clearpath_stats.xpoint_calls));
    fprintf(fp, "  \"avg_candidates_per_attempt\": %.6f\n",
        clearpath_stats_avg(s_clearpath_stats.candidate_points_total,
            s_clearpath_stats.attempts));
    fprintf(fp, "}\n");
    fclose(fp);

    fprintf(stderr, "PF_CLEARPATH_STATS wrote %s\n", s_clearpath_stats.path);
}

static bool same_position(vec2_t a, vec2_t b)
{
    vec2_t delta;
    PFM_Vec2_Sub(&b, &a, &delta);
    return (PFM_Vec2_Len(&delta) < EPSILON);
}

static void compute_vo_edges(struct cp_ent ent, struct cp_ent neighb,
                             vec2_t *out_xz_right, vec2_t *out_xz_left)
{
    vec2_t ent_to_nb, right;
    PFM_Vec2_Sub(&neighb.xz_pos, &ent.xz_pos, &ent_to_nb);
    PFM_Vec2_Normal(&ent_to_nb, &ent_to_nb);

    right = (vec2_t){-ent_to_nb.z, ent_to_nb.x};
    PFM_Vec2_Scale(&right, neighb.radius + ent.radius + CLEARPATH_BUFFER_RADIUS, &right);

    vec2_t right_tangent, left_tangent;
    PFM_Vec2_Add(&neighb.xz_pos, &right, &right_tangent);
    PFM_Vec2_Sub(&neighb.xz_pos, &right, &left_tangent);

    PFM_Vec2_Sub(&right_tangent, &ent.xz_pos, out_xz_right);
    PFM_Vec2_Normal(out_xz_right, out_xz_right);
    assert(fabs(PFM_Vec2_Len(out_xz_right) - 1.0f) < EPSILON);

    PFM_Vec2_Sub(&left_tangent, &ent.xz_pos, out_xz_left);
    PFM_Vec2_Normal(out_xz_left, out_xz_left);
    assert(fabs(PFM_Vec2_Len(out_xz_left) - 1.0f) < EPSILON);
}

static struct VO compute_vo(struct cp_ent ent, struct cp_ent neighb)
{
    struct VO ret;
    compute_vo_edges(ent, neighb, &ret.xz_right_side, &ret.xz_left_side);
    PFM_Vec2_Add(&ent.xz_pos, &neighb.xz_vel, &ret.xz_apex);
    return ret;
}

static struct RVO compute_rvo(struct cp_ent ent, struct cp_ent neighb)
{
    struct RVO ret;
    compute_vo_edges(ent, neighb, &ret.xz_right_side, &ret.xz_left_side);

    vec2_t apex_off;
    PFM_Vec2_Add(&ent.xz_vel, &neighb.xz_vel, &apex_off);
    PFM_Vec2_Scale(&apex_off, 0.5f, &apex_off);
    PFM_Vec2_Add(&ent.xz_pos, &apex_off, &ret.xz_apex);

    return ret;
}

static struct HRVO compute_hrvo(struct cp_ent ent, struct cp_ent neighb)
{
    struct HRVO ret;
    struct RVO rvo = compute_rvo(ent, neighb);
    struct line_2d l1, l2;
    vec2_t intersec_point;

    vec2_t centerline;
    PFM_Vec2_Add(&rvo.xz_left_side, &rvo.xz_right_side, &centerline);

    vec2_t vo_apex;
    PFM_Vec2_Add(&ent.xz_pos, &neighb.xz_vel, &vo_apex);

    float det = (centerline.x * ent.xz_vel.y) - (centerline.y * ent.xz_vel.x);
    if(det > EPSILON) { /* the entity velocity is left of the RVO centerline */

        l1 = (struct line_2d){rvo.xz_apex, rvo.xz_left_side};
        l2 = (struct line_2d){vo_apex, rvo.xz_right_side};

        bool collide = C_InfiniteLineIntersection(l1, l2, &intersec_point);
        assert(collide);
        ret.xz_apex = intersec_point;

    }else if(det < -EPSILON) { /* the entity velocity is right of the RVO centerline */

        l1 = (struct line_2d){rvo.xz_apex, rvo.xz_right_side};
        l2 = (struct line_2d){vo_apex, rvo.xz_left_side};

        bool collide = C_InfiniteLineIntersection(l1, l2, &intersec_point);
        assert(collide);
        ret.xz_apex = intersec_point;
    
    }else{ /* The entity velocity is right on the centerline */

        ret.xz_apex = rvo.xz_apex;
    }
    
    ret.xz_right_side = rvo.xz_right_side;
    ret.xz_left_side = rvo.xz_left_side;
    return ret;
}

static size_t compute_all_vos(struct cp_ent ent, vec_cp_ent_t stat_neighbs, 
                              struct VO *out)
{
    size_t ret = 0; 

    for(struct cp_ent *nb = stat_neighbs.array; 
        nb < stat_neighbs.array + vec_size(&stat_neighbs); nb++) {

        if(same_position(ent.xz_pos, nb->xz_pos))
            continue;
        out[ret++] = compute_vo(ent, *nb);
    }

    return ret;
}

static size_t compute_all_hrvos(struct cp_ent ent, vec_cp_ent_t dyn_neighbs, 
                                struct HRVO *out)
{
    size_t ret = 0; 

    for(int i = 0; i < vec_size(&dyn_neighbs); i++) {

        struct cp_ent *nb = &vec_AT(&dyn_neighbs, i);
        if(same_position(ent.xz_pos, nb->xz_pos))
            continue;
        out[ret++] = compute_hrvo(ent, *nb);
    }

    return ret;
}

static inline bool det_less_than_eps_len(float det, float len_sq)
{
    return det < 0.0f || (det * det) < (EPSILON_SQ * len_sq);
}

static inline bool det_greater_than_neg_eps_len(float det, float len_sq)
{
    return det > 0.0f || (det * det) < (EPSILON_SQ * len_sq);
}

/* Points exactly 'on' the boundary will be considered as 'not inside' of the PCR for our purposes. */
static bool inside_pcr(const struct line_2d *vo_lr_pairs, size_t n_rays, vec2_t test)
{
    assert(n_rays % 2 == 0);
    uint64_t timing_begin = clearpath_timing_begin();
    uint64_t ray_pair_tests = 0;
    uint64_t apex_skips = 0;

    for(int i = 0; i < n_rays; i+=2) {

        ray_pair_tests++;

        assert(fabs(PFM_Vec2_Len(&vo_lr_pairs[i + 0].dir) - 1.0f) < EPSILON);
        const float left_dir_x = vo_lr_pairs[i + 0].dir.x;
        const float left_dir_z = vo_lr_pairs[i + 0].dir.z;

        float point_to_test_x = test.x - vo_lr_pairs[i + 0].point.x;
        float point_to_test_z = test.z - vo_lr_pairs[i + 0].point.z;
        float point_to_test_len_sq = point_to_test_x * point_to_test_x
            + point_to_test_z * point_to_test_z;
        if(point_to_test_len_sq < EPSILON_SQ) {
            apex_skips++;
            continue;
        }

        float left_det = (point_to_test_z * left_dir_x) - (point_to_test_x * left_dir_z);
        bool left_of_vo = det_less_than_eps_len(left_det, point_to_test_len_sq);

        if(left_of_vo)
            continue;

        assert(fabs(PFM_Vec2_Len(&vo_lr_pairs[i + 1].dir) - 1.0f) < EPSILON);
        const float right_dir_x = vo_lr_pairs[i + 1].dir.x;
        const float right_dir_z = vo_lr_pairs[i + 1].dir.z;

        point_to_test_x = test.x - vo_lr_pairs[i + 1].point.x;
        point_to_test_z = test.z - vo_lr_pairs[i + 1].point.z;
        point_to_test_len_sq = point_to_test_x * point_to_test_x
            + point_to_test_z * point_to_test_z;
        if(point_to_test_len_sq < EPSILON_SQ) {
            apex_skips++;
            continue;
        }

        float right_det = (point_to_test_z * right_dir_x) - (point_to_test_x * right_dir_z);
        bool right_of_vo = det_greater_than_neg_eps_len(right_det, point_to_test_len_sq);

        if(right_of_vo)
            continue;

        assert(!left_of_vo && !right_of_vo);
        clearpath_stats_add(&s_clearpath_stats.inside_pcr_calls, 1);
        clearpath_stats_add(&s_clearpath_stats.inside_pcr_ray_pair_tests, ray_pair_tests);
        clearpath_stats_add(&s_clearpath_stats.inside_pcr_apex_skips, apex_skips);
        clearpath_stats_add(&s_clearpath_stats.inside_pcr_hits, 1);
        clearpath_stats_timing(CLEARPATH_TIMING_INSIDE_PCR, timing_begin);
        return true;
    }

    clearpath_stats_add(&s_clearpath_stats.inside_pcr_calls, 1);
    clearpath_stats_add(&s_clearpath_stats.inside_pcr_ray_pair_tests, ray_pair_tests);
    clearpath_stats_add(&s_clearpath_stats.inside_pcr_apex_skips, apex_skips);
    clearpath_stats_add(&s_clearpath_stats.inside_pcr_misses, 1);
    clearpath_stats_timing(CLEARPATH_TIMING_INSIDE_PCR, timing_begin);
    return false;
}

static bool ray_ray_intersection_fast(struct line_2d l1, struct line_2d l2, vec2_t *out_xz)
{
    float denom = l1.dir.x * l2.dir.z - l1.dir.z * l2.dir.x;
    if(fabsf(denom) < EPSILON)
        return false;

    float delta_x = l2.point.x - l1.point.x;
    float delta_z = l2.point.z - l1.point.z;
    float t = (delta_x * l2.dir.z - delta_z * l2.dir.x) / denom;
    if(t < 0.0f)
        return false;

    float u = (delta_x * l1.dir.z - delta_z * l1.dir.x) / denom;
    if(u < 0.0f)
        return false;

    out_xz->x = l1.point.x + t * l1.dir.x;
    out_xz->z = l1.point.z + t * l1.dir.z;
    return true;
}

static void rays_repr(const struct HRVO *hrvos, size_t n_hrvos,
                      const struct VO *vos, size_t n_vos,
                      struct line_2d *out)
{
    size_t rays_idx  = 0;

    for(int i = 0; i < n_hrvos; i++) {
         
        out[rays_idx + 0].point = hrvos[i].xz_apex;
        out[rays_idx + 0].dir = hrvos[i].xz_left_side;

        out[rays_idx + 1].point = hrvos[i].xz_apex;
        out[rays_idx + 1].dir = hrvos[i].xz_right_side;

        rays_idx += 2;
    }

    for(int i = 0; i < n_vos; i++) {
    
        out[rays_idx + 0].point = vos[i].xz_apex;
        out[rays_idx + 0].dir = vos[i].xz_left_side;

        out[rays_idx + 1].point = vos[i].xz_apex;
        out[rays_idx + 1].dir = vos[i].xz_right_side;

        rays_idx += 2;
    }
}

static size_t compute_vo_xpoints(struct line_2d *rays, size_t n_rays, vec_vec2_t *inout)
{
    uint64_t timing_begin = clearpath_timing_begin();
    size_t ret = 0;
    uint64_t ray_pair_tests = 0;
    uint64_t ray_pair_intersections = 0;
    uint64_t inside_rejected = 0;

    for(int i = 0; i < n_rays; i++) {
    for(int j = i + 1; j < n_rays; j++) {

        ray_pair_tests++;

        vec2_t isec_point;
        if(!ray_ray_intersection_fast(rays[i], rays[j], &isec_point))
            continue;

        ray_pair_intersections++;

        if(inside_pcr(rays, n_rays, isec_point)) {
            inside_rejected++;
            continue;
        }

        vec_vec2_push(inout, isec_point);
        ret++;
    }}

    clearpath_stats_add(&s_clearpath_stats.xpoint_calls, 1);
    clearpath_stats_add(&s_clearpath_stats.xpoint_ray_pair_tests, ray_pair_tests);
    clearpath_stats_add(&s_clearpath_stats.xpoint_ray_pair_intersections, ray_pair_intersections);
    clearpath_stats_add(&s_clearpath_stats.xpoint_inside_rejected, inside_rejected);
    clearpath_stats_add(&s_clearpath_stats.xpoint_accepted, ret);
    clearpath_stats_timing(CLEARPATH_TIMING_XPOINTS, timing_begin);
    return ret;
}

static size_t compute_vdes_proj_points(struct line_2d *rays, size_t n_rays,
                                       vec2_t des_v, vec_vec2_t *inout)
{
    uint64_t timing_begin = clearpath_timing_begin();
    vec2_t proj;
    size_t ret = 0;
    uint64_t projection_tests = 0;

    for(int i = 0; i < n_rays; i++) {
    
        assert(fabs(PFM_Vec2_Len(&rays[i].dir) - 1.0f) < EPSILON);

        float len = PFM_Vec2_Dot(&rays[i].dir, &des_v);
        PFM_Vec2_Scale(&rays[i].dir, len, &proj);
        PFM_Vec2_Add(&rays[i].point, &proj, &proj);

        projection_tests++;
        if(!inside_pcr(rays, n_rays, proj)) {
        
            vec_vec2_push(inout, proj);
            ret++;
        }
    }

    clearpath_stats_add(&s_clearpath_stats.projection_calls, 1);
    clearpath_stats_add(&s_clearpath_stats.projection_tests, projection_tests);
    clearpath_stats_add(&s_clearpath_stats.projection_accepted, ret);
    clearpath_stats_timing(CLEARPATH_TIMING_PROJECTION, timing_begin);
    return ret;
}

static vec2_t compute_vnew(const vec_vec2_t *outside_points, vec2_t des_v, vec2_t ent_xz_pos)
{
    float min_dist = INFINITY, len;
    vec2_t ret = (vec2_t){0.0f, 0.0f};

    for(int i = 0; i < vec_size(outside_points); i++) {

        /* The points are in worldspace coordinates. Convert them to the entity's 
         * local space to get the admissible velocities. */
        vec2_t curr = vec_AT(outside_points, i), diff;
        PFM_Vec2_Sub(&curr, &ent_xz_pos, &curr);

        PFM_Vec2_Sub(&des_v, &curr, &diff);
        if((len = PFM_Vec2_Len(&diff)) < min_dist) {

            min_dist = len;
            ret = curr;
        }
    }
    return ret;
}

static bool remove_furthest(vec2_t xz_pos, vec_cp_ent_t *dyn_inout, vec_cp_ent_t *stat_inout)
{
    float max_dist = -INFINITY;
    vec_cp_ent_t *del_vec = NULL;
    int del_idx = -1;

    for(int i = 0; i < 2; i++) {
    
        vec_cp_ent_t *curr_vec = (i == 0) ? dyn_inout : stat_inout;
        for(int j = 0; j < vec_size(curr_vec); j++) {
        
            float len;
            vec2_t diff;
            struct cp_ent *ent = &vec_AT(curr_vec, j);

            PFM_Vec2_Sub(&xz_pos, &ent->xz_pos, &diff);
            if((len = PFM_Vec2_Len(&diff)) > max_dist) {
                max_dist = len; 
                del_vec = curr_vec;
                del_idx = j;
            }
        }
    }

    if(max_dist > -INFINITY) {
        assert(del_idx != -1);
        vec_cp_ent_del(del_vec, del_idx);
        return true;
    }
    return false;
}

static void cap_constraint_neighbours(vec2_t xz_pos,
                                      vec_cp_ent_t *dyn_inout,
                                      vec_cp_ent_t *stat_inout)
{
    if(s_max_constraint_neighbs == 0)
        return;

    size_t total = vec_size(dyn_inout) + vec_size(stat_inout);
    if(total <= s_max_constraint_neighbs)
        return;

    clearpath_stats_add(&s_clearpath_stats.constraint_cap_attempts, 1);
    clearpath_stats_max(&s_clearpath_stats.constraint_cap_max_input_neighbours, total);

    size_t removed = 0;
    while(total > s_max_constraint_neighbs) {
        if(!remove_furthest(xz_pos, dyn_inout, stat_inout))
            break;
        total--;
        removed++;
    }
    clearpath_stats_add(&s_clearpath_stats.constraint_cap_removes, removed);
}

static void on_render_3d(void *user, void *event)
{
    if(!s_debug_saved.valid)
        return;

    size_t idx = 0;

    const struct map *map = user;
    const struct cp_ent *cpent = &s_debug_saved.cpent;
    const size_t n_vos = s_debug_saved.n_hrvos + s_debug_saved.n_vos;

    vec3_t yellow = (vec3_t){1.0f, 1.0f, 0.0f};
    vec3_t blue = (vec3_t){0.0f, 0.0f, 1.0f};
    vec3_t green = (vec3_t){0.0f, 1.0f, 0.0f};

    STALLOC(vec2_t, apexes, n_vos);
    STALLOC(vec2_t, left_rays, n_vos);
    STALLOC(vec2_t, right_rays, n_vos);

    for(int i = 0; i < s_debug_saved.n_hrvos; i++, idx++) {
        apexes[idx] = s_debug_saved.hrvos[i].xz_apex;
        left_rays[idx] = s_debug_saved.hrvos[i].xz_left_side; 
        right_rays[idx] = s_debug_saved.hrvos[i].xz_right_side; 
    }

    for(int i = 0; i < s_debug_saved.n_vos; i++, idx++) {
        apexes[idx] = s_debug_saved.vos[i].xz_apex;
        left_rays[idx] = s_debug_saved.vos[i].xz_left_side; 
        right_rays[idx] = s_debug_saved.vos[i].xz_right_side; 
    }

    assert(idx == n_vos);
    R_PushCmd((struct rcmd){
        .func = R_Cmd_DrawCombinedHRVO,
        .nargs = 5,
        .args = {
            R_PushArg(apexes, n_vos * sizeof(vec2_t)),
            R_PushArg(left_rays, n_vos * sizeof(vec2_t)),
            R_PushArg(right_rays, n_vos * sizeof(vec2_t)),
            R_PushArg(&n_vos, sizeof(n_vos)),
            (void*)G_GetPrevTickMap(),
        },
    });

    float radius = CLEARPATH_NEIGHBOUR_RADIUS;
    float width = 0.5f;

    R_PushCmd((struct rcmd){
        .func = R_Cmd_DrawSelectionCircle,
        .nargs = 5,
        .args = {
            R_PushArg(&cpent->xz_pos, sizeof(cpent->xz_pos)),
            R_PushArg(&radius, sizeof(radius)),
            R_PushArg(&width, sizeof(width)),
            R_PushArg(&yellow, sizeof(yellow)),
            (void*)G_GetPrevTickMap(),
        },
    });

    mat4x4_t ident;
    PFM_Mat4x4_Identity(&ident);

    vec3_t origin_pos = (vec3_t){
        cpent->xz_pos.x, 
        M_HeightAtPoint(map, cpent->xz_pos) + 5.0f, 
        cpent->xz_pos.z
    };

    vec2_t des_v = s_debug_saved.ent_des_v;
    vec3_t des_vel_dir = (vec3_t){des_v.x, 0.0f, des_v.z};
    PFM_Vec3_Normal(&des_vel_dir, &des_vel_dir);

    float t = PFM_Vec2_Len(&des_v) * G_Move_GetTickHz();
    R_PushCmd((struct rcmd){
        .func = R_Cmd_DrawRay,
        .nargs = 5,
        .args = {
            R_PushArg(&origin_pos, sizeof(origin_pos)),
            R_PushArg(&des_vel_dir, sizeof(des_vel_dir)),
            R_PushArg(&ident, sizeof(ident)),
            R_PushArg(&blue, sizeof(blue)),
            R_PushArg(&t, sizeof(t)),
        },
    });

    vec2_t v_new = s_debug_saved.v_new;
    vec3_t vel_dir = (vec3_t){v_new.x, 0.0f, v_new.z};
    PFM_Vec3_Normal(&vel_dir, &vel_dir);

    t = PFM_Vec2_Len(&v_new) * G_Move_GetTickHz();
    R_PushCmd((struct rcmd){
        .func = R_Cmd_DrawRay,
        .nargs = 5,
        .args = {
            R_PushArg(&origin_pos, sizeof(origin_pos)),
            R_PushArg(&vel_dir, sizeof(vel_dir)),
            R_PushArg(&ident, sizeof(ident)),
            R_PushArg(&green, sizeof(green)),
            R_PushArg(&t, sizeof(t)),
        },
    });

    radius = 1.0f;
    width = 1.0f;

    for(int i = 0; i < vec_size(&s_debug_saved.xpoints); i++) {

        R_PushCmd((struct rcmd){
            .func = R_Cmd_DrawSelectionCircle,
            .nargs = 5,
            .args = {
                R_PushArg(&vec_AT(&s_debug_saved.xpoints, i), sizeof(vec_AT(&s_debug_saved.xpoints, 0))),
                R_PushArg(&radius, sizeof(radius)),
                R_PushArg(&width, sizeof(width)),
                R_PushArg(&green, sizeof(green)),
                (void*)G_GetPrevTickMap(),
            },
        });
    }

    char strbuff[256];
    pf_strlcpy(strbuff, "Desired Velocity in PCR:", sizeof(strbuff));
    pf_strlcat(strbuff, s_debug_saved.des_v_in_pcr ? "true" : "false", sizeof(strbuff));
    struct rgba text_color = s_debug_saved.des_v_in_pcr ? (struct rgba){255, 0, 0, 255}
                                                        : (struct rgba){0, 255, 0, 255};
    UI_DrawText(strbuff, (struct rect){5,50,200,50}, text_color);

    STFREE(apexes);
    STFREE(left_rays);
    STFREE(right_rays);
}

static bool clearpath_new_velocity(struct cp_ent cpent,
                                   uint32_t ent_uid,
                                   vec2_t ent_des_v,
                                   const vec_cp_ent_t dyn_neighbs,
                                   const vec_cp_ent_t stat_neighbs,
                                   bool save_debug,
                                   vec2_t *out)
{
    bool status = false;
    STALLOC(struct HRVO, dyn_hrvos, vec_size(&dyn_neighbs));
    STALLOC(struct VO, stat_vos, vec_size(&stat_neighbs));

    clearpath_stats_add(&s_clearpath_stats.attempts, 1);
    clearpath_stats_add(&s_clearpath_stats.dynamic_neighbours, vec_size(&dyn_neighbs));
    clearpath_stats_add(&s_clearpath_stats.static_neighbours, vec_size(&stat_neighbs));

    uint64_t timing_begin = clearpath_timing_begin();
    size_t n_hrvos = compute_all_hrvos(cpent, dyn_neighbs, dyn_hrvos);
    size_t n_vos = compute_all_vos(cpent, stat_neighbs, (struct VO*)stat_vos);

    /* We may have skipped the neighbours that are at the exact same 
     * or nearly same position as the entity.
     */
    assert(n_hrvos <= vec_size(&dyn_neighbs));
    assert(n_vos <= vec_size(&stat_neighbs));

    /* Following the ClearPath approach, which is applicable to many variations 
     * of velocity obstacles, we represent the combined hybrid reciprocal velocity 
     * obstacle as a union of line segments. 
     */
    const size_t n_rays = (n_hrvos + n_vos) * 2;
    clearpath_stats_add(&s_clearpath_stats.hrvos, n_hrvos);
    clearpath_stats_add(&s_clearpath_stats.vos, n_vos);
    clearpath_stats_add(&s_clearpath_stats.rays, n_rays);
    clearpath_stats_max(&s_clearpath_stats.max_rays, n_rays);

    STALLOC(struct line_2d, rays, n_rays);
    rays_repr(dyn_hrvos, n_hrvos, stat_vos, n_vos, rays);
    clearpath_stats_timing(CLEARPATH_TIMING_ATTEMPT_SETUP, timing_begin);

    if(save_debug) {

        size_t nsaved_hrvos = n_hrvos <= MAX_SAVED_VOS ? n_hrvos : MAX_SAVED_VOS;
        memcpy(s_debug_saved.hrvos, dyn_hrvos, nsaved_hrvos * sizeof(struct HRVO));
        s_debug_saved.n_hrvos = nsaved_hrvos;

        size_t nsaved_vos = n_vos <= MAX_SAVED_VOS ? n_vos : MAX_SAVED_VOS;
        memcpy(s_debug_saved.vos, stat_vos, nsaved_vos * sizeof(struct VO));
        s_debug_saved.n_vos = nsaved_vos;

        vec_vec2_reset(&s_debug_saved.xpoints);

        s_debug_saved.cpent = cpent;
        s_debug_saved.ent_des_v = ent_des_v;
        s_debug_saved.v_new = ent_des_v;
        s_debug_saved.valid = true;
    }

    vec2_t des_v_ws;
    PFM_Vec2_Add(&cpent.xz_pos, &ent_des_v, &des_v_ws);

    timing_begin = clearpath_timing_begin();
    if(!inside_pcr(rays, n_rays, des_v_ws)) {
        clearpath_stats_timing(CLEARPATH_TIMING_DESIRED_PCR, timing_begin);

        clearpath_stats_add(&s_clearpath_stats.desired_outside_pcr, 1);
        s_debug_saved.des_v_in_pcr = false;
        *out = ent_des_v;
        status = true;
        goto out;
    }
    clearpath_stats_timing(CLEARPATH_TIMING_DESIRED_PCR, timing_begin);
    clearpath_stats_add(&s_clearpath_stats.desired_inside_pcr, 1);

    vec_vec2_t xpoints;
    vec_vec2_init(&xpoints);

    /* The line segments are intersected pairwise and the intersection points 
     * inside the combined hybrid reciprocal velocity obstacle are discarded. 
     * The remaining intersection points are permissible new velocities on the 
     * boundary of the combined hybrid reciprocal velocity obstacle.
     */
    compute_vo_xpoints(rays, n_rays, &xpoints); 

    /* In addition we project the preferred velocity (des_v) on to the line 
     * segments (xz_left_side and xz_right_side of each hrvo) and also retain 
     * those points that are outside the combined hybrid reciprocal velocity 
     * obstacle.
     */
    compute_vdes_proj_points(rays, n_rays, ent_des_v, &xpoints);

    clearpath_stats_add(&s_clearpath_stats.candidate_points_total, vec_size(&xpoints));
    clearpath_stats_max(&s_clearpath_stats.max_candidate_points, vec_size(&xpoints));

    if(vec_size(&xpoints) == 0) {
        clearpath_stats_add(&s_clearpath_stats.no_solution_attempts, 1);
        vec_vec2_destroy(&xpoints);
        goto out;    
    }

    timing_begin = clearpath_timing_begin();
    vec2_t ret = compute_vnew(&xpoints, ent_des_v, cpent.xz_pos);
    clearpath_stats_timing(CLEARPATH_TIMING_COMPUTE_VNEW, timing_begin);

    if(save_debug) {
    
        vec_vec2_copy(&s_debug_saved.xpoints, &xpoints);
        s_debug_saved.v_new = ret;
        s_debug_saved.des_v_in_pcr = true;
    }

    vec_vec2_destroy(&xpoints);
    *out = ret;
    status = true;

out:
    STFREE(dyn_hrvos);
    STFREE(stat_vos);
    STFREE(rays);
    return status;
}

static bool entities_equal(uint32_t *a, uint32_t *b)
{
    return ((*a) == (*b));
}

/*****************************************************************************/
/* EXTERN FUNCTIONS                                                          */
/*****************************************************************************/

bool G_ClearPath_ShouldSaveDebug(uint32_t ent_uid)
{
    ASSERT_IN_MAIN_THREAD();

    struct sval setting;
    ss_e status = Settings_Get("pf.debug.show_first_sel_combined_hrvo", &setting);
    assert(status == SS_OKAY);

    if(!setting.as_bool)
        return false;

    enum selection_type seltype;
    const vec_entity_t *sel = G_Sel_Get(&seltype);

    if(vec_size(sel) == 0)
        return false; 

    return (0 == vec_entity_indexof((vec_entity_t*)sel, ent_uid, entities_equal));
}

void G_ClearPath_Init(const struct map *map)
{
    clearpath_config_init();
    clearpath_stats_init();
    E_Global_Register(EVENT_RENDER_3D_POST, on_render_3d, (struct map*)map, 
        G_RUNNING | G_PAUSED_FULL | G_PAUSED_UI_RUNNING);
    vec_vec2_init(&s_debug_saved.xpoints);
}

void G_ClearPath_Shutdown(void)
{
    clearpath_stats_write();
    E_Global_Unregister(EVENT_RENDER_3D_POST, on_render_3d);
    vec_vec2_destroy(&s_debug_saved.xpoints);
}

void G_ClearPath_WriteStats(void)
{
    clearpath_stats_write();
}

vec2_t G_ClearPath_NewVelocity(struct cp_ent cpent,
                               uint32_t ent_uid,
                               vec2_t ent_des_v,
                               vec_cp_ent_t dyn_neighbs,
                               vec_cp_ent_t stat_neighbs,
                               bool save_debug)
{
    PERF_ENTER();
    clearpath_stats_add(&s_clearpath_stats.calls, 1);

    size_t removed_total = 0;

    uint64_t timing_begin = clearpath_timing_begin();
    cap_constraint_neighbours(cpent.xz_pos, &dyn_neighbs, &stat_neighbs);
    clearpath_stats_timing(CLEARPATH_TIMING_CONSTRAINT_CAP, timing_begin);

    do{
        vec2_t ret;
        bool found = clearpath_new_velocity(cpent, ent_uid, ent_des_v, 
            dyn_neighbs, stat_neighbs, save_debug, &ret);
        if(found) {
            clearpath_stats_add(&s_clearpath_stats.successes, 1);
            PERF_RETURN(ret);
        }

        clearpath_stats_add(&s_clearpath_stats.fallback_retry_steps, 1);

        size_t curr_neighbs = vec_size(&dyn_neighbs) + vec_size(&stat_neighbs);
        size_t batch = (curr_neighbs >= s_fallback_batch_min_neighbs)
            ? s_fallback_remove_batch : 1;

        for(size_t i = 0; i < batch; i++) {
            if(s_fallback_max_removes > 0 && removed_total >= s_fallback_max_removes) {
                clearpath_stats_add(&s_clearpath_stats.fallback_cap_returns, 1);
                clearpath_stats_add(&s_clearpath_stats.zero_velocity_returns, 1);
                PERF_RETURN((vec2_t){0.0f, 0.0f});
            }
            if(vec_size(&dyn_neighbs) == 0 || vec_size(&stat_neighbs) == 0)
                break;
            timing_begin = clearpath_timing_begin();
            if(!remove_furthest(cpent.xz_pos, &dyn_neighbs, &stat_neighbs))
                break;
            clearpath_stats_timing(CLEARPATH_TIMING_FALLBACK_REMOVE, timing_begin);
            removed_total++;
            clearpath_stats_add(&s_clearpath_stats.fallback_removes, 1);
        }

    }while(vec_size(&dyn_neighbs) > 0 && vec_size(&stat_neighbs) > 0);

    clearpath_stats_add(&s_clearpath_stats.zero_velocity_returns, 1);
    PERF_RETURN((vec2_t){0.0f, 0.0f});
}
