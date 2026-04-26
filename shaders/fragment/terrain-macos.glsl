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

#version 330 core

#define SPECULAR_STRENGTH  0.5
#define SPECULAR_SHININESS 2

#define Y_COORDS_PER_TILE  4 
#define X_COORDS_PER_TILE  8 
#define Z_COORDS_PER_TILE  8 

#define EXTRA_AMBIENT_PER_LEVEL 0.03

#define BLEND_MODE_NOBLEND  0
#define BLEND_MODE_BLUR     1

#define TERRAIN_AMBIENT     float(0.7)
#define TERRAIN_DIFFUSE     vec3(0.9, 0.9, 0.9)
#define TERRAIN_SPECULAR    vec3(0.1, 0.1, 0.1)

#define STATE_UNEXPLORED 0
#define STATE_IN_FOG     1
#define STATE_VISIBLE    2

/*****************************************************************************/
/* INPUTS                                                                    */
/*****************************************************************************/

in VertexToFrag {
         vec2  uv;
    flat int   mat_idx;
         vec3  world_pos;
         vec3  normal;
    flat int   blend_mode;
    flat int   no_bump_map;
    flat int   mid_indices;
    flat ivec2 c1_indices;
    flat ivec2 c2_indices;
    flat int   tb_indices;
    flat int   lr_indices;
    flat int   wang_index;
         vec4  light_space_pos;
}from_vertex;

/*****************************************************************************/
/* OUTPUTS                                                                   */
/*****************************************************************************/

out vec4 o_frag_color;

/*****************************************************************************/
/* UNIFORMS                                                                  */
/*****************************************************************************/

uniform vec3 ambient_color;
uniform vec3 light_color;
uniform vec3 light_pos;
uniform vec3 view_pos;

uniform sampler2DArray tex_array0;

uniform usamplerBuffer visbuff;
uniform int visbuff_offset;

uniform ivec4 map_resolution;
uniform vec2 map_pos;

/*****************************************************************************/
/* PROGRAM                                                                   */
/*****************************************************************************/

ivec4 tile_desc_at(vec3 ws_pos)
{
    int tile_w = map_resolution[2];
    int tile_h = map_resolution[3];

    int chunk_x_dist = tile_w * X_COORDS_PER_TILE;
    int chunk_z_dist = tile_h * Z_COORDS_PER_TILE;

    int chunk_r = int(abs(map_pos.y - ws_pos.z) / chunk_z_dist);
    int chunk_c = int(abs(map_pos.x - ws_pos.x) / chunk_x_dist);

    int chunk_base_x = int(map_pos.x - (chunk_c * chunk_x_dist));
    int chunk_base_z = int(map_pos.y + (chunk_r * chunk_z_dist));

    int tile_c = int(abs(chunk_base_x - ws_pos.x) / X_COORDS_PER_TILE);
    int tile_r = int(abs(chunk_base_z - ws_pos.z) / Z_COORDS_PER_TILE);

    return ivec4(chunk_r, chunk_c, tile_r, tile_c);
}

ivec4 tile_relative_desc(ivec4 desc, int dr, int dc)
{
    int abs_r = desc.x * map_resolution.z + desc.z + dr;
    int abs_c = desc.y * map_resolution.a + desc.a + dc;

    abs_r = clamp(abs_r, 0, map_resolution.x * map_resolution.z - 1);
    abs_c = clamp(abs_c, 0, map_resolution.y * map_resolution.a - 1);

    return ivec4(
        abs_r / map_resolution.z,
        abs_c / map_resolution.a,
        int(mod(abs_r, map_resolution.z)),
        int(mod(abs_c, map_resolution.a))
    );
}

int visbuff_idx(ivec4 td)
{
    int chunk_w = map_resolution[0];
    int tile_w = map_resolution[2];
    int tile_h = map_resolution[3];
    int tiles_per_chunk = tile_w * tile_h;

    return visbuff_offset + (td.x * tiles_per_chunk * chunk_w)
                          + (td.y * tiles_per_chunk)
                          + (td.z * tile_w)
                          + td.a;
}

float tf_for_state(uint state)
{
    if(state == uint(STATE_UNEXPLORED))
        return 0.0;
    else if(state == uint(STATE_IN_FOG))
        return 0.5;
    return 1.0;
}

float bilinear_interp_unit_square(float tl, float tr, float bl, float br, vec2 coord)
{
    return bl * (1.0 - coord.x) * (1.0 - coord.y)
         + br * coord.x * (1.0 - coord.y)
         + tl * (1.0 - coord.x) * coord.y
         + tr * coord.x * coord.y;
}

uvec4 fetch_safe(usamplerBuffer buff, int idx)
{
    int batch_size = map_resolution[0] * map_resolution[1] * map_resolution[2] * map_resolution[3];
    int buff_size = textureSize(buff);
    int begin_idx = visbuff_offset;
    int end_idx = int(mod(visbuff_offset + batch_size, buff_size));

    if(end_idx > begin_idx) {
        idx = clamp(idx, begin_idx, end_idx - 1);
    }else{
        int dist = begin_idx - end_idx;
        if(idx < end_idx + dist / 2)
            idx = clamp(idx, 0, end_idx - 1);
        else
            idx = clamp(idx, begin_idx, buff_size - 1);
    }
    return texelFetch(buff, idx);
}

float tint_factor(ivec4 td, vec2 uv)
{
    float c  = tf_for_state(fetch_safe(visbuff, visbuff_idx(td)).r);
    float tl = tf_for_state(fetch_safe(visbuff, visbuff_idx(tile_relative_desc(td, -1, -1))).r);
    float tr = tf_for_state(fetch_safe(visbuff, visbuff_idx(tile_relative_desc(td, -1, +1))).r);
    float l  = tf_for_state(fetch_safe(visbuff, visbuff_idx(tile_relative_desc(td,  0, -1))).r);
    float r  = tf_for_state(fetch_safe(visbuff, visbuff_idx(tile_relative_desc(td,  0, +1))).r);
    float bl = tf_for_state(fetch_safe(visbuff, visbuff_idx(tile_relative_desc(td, +1, -1))).r);
    float br = tf_for_state(fetch_safe(visbuff, visbuff_idx(tile_relative_desc(td, +1, +1))).r);
    float t  = tf_for_state(fetch_safe(visbuff, visbuff_idx(tile_relative_desc(td, -1,  0))).r);
    float b  = tf_for_state(fetch_safe(visbuff, visbuff_idx(tile_relative_desc(td, +1,  0))).r);

    float tl_corner = (c + t + l + tl) / 4.0;
    float tr_corner = (c + t + r + tr) / 4.0;
    float bl_corner = (c + l + b + bl) / 4.0;
    float br_corner = (c + r + b + br) / 4.0;

    return bilinear_interp_unit_square(tl_corner, tr_corner, bl_corner, br_corner, uv);
}

vec4 texture_val_raw(int mat_idx, int wang_idx, vec2 uv)
{
    int idx = mat_idx * 8;
    if(idx < textureSize(tex_array0, 0).z) {
        return texture(tex_array0, vec3(uv.x, 1.0 - uv.y, idx + wang_idx));
    }
    return vec4(0.0, 0.0, 0.0, 0.0);
}

vec4 texture_val(int mat_idx, int wang_idx, vec2 uv)
{
    return texture_val_raw(mat_idx, wang_idx, uv);
}

vec4 mixed_texture_val(ivec2 adjacency_mats, int wang_idx, vec2 uv)
{
    vec4 ret = vec4(0.0);
    for(int i = 0; i < 2; i++) {
    for(int j = 0; j < 4; j++) {
        int idx = (adjacency_mats[i] >> (j * 8)) & 0xff;
        ret += texture_val(idx, wang_idx, uv) * (1.0 / 8.0);
    }}
    return ret;
}

vec4 bilinear_interp_vec4
(
    vec4 q11, vec4 q12, vec4 q21, vec4 q22,
    float x1, float x2,
    float y1, float y2,
    float x, float y
)
{
    float x2x1 = x2 - x1;
    float y2y1 = y2 - y1;
    float x2x = x2 - x;
    float y2y = y2 - y;
    float yy1 = y - y1;
    float xx1 = x - x1;

    return 1.0 / (x2x1 * y2y1) * (
        q11 * x2x * y2y +
        q21 * xx1 * y2y +
        q12 * x2x * yy1 +
        q22 * xx1 * yy1
    );
}

vec4 blended_texture_val()
{
    vec4 tex_color;

    bool bot = (from_vertex.uv.x > from_vertex.uv.y) && (1.0 - from_vertex.uv.x > from_vertex.uv.y);
    bool top = (from_vertex.uv.x < from_vertex.uv.y) && (1.0 - from_vertex.uv.x < from_vertex.uv.y);
    bool left = (from_vertex.uv.x < from_vertex.uv.y) && (1.0 - from_vertex.uv.x > from_vertex.uv.y);
    bool right = (from_vertex.uv.x > from_vertex.uv.y) && (1.0 - from_vertex.uv.x < from_vertex.uv.y);

    bool left_half = from_vertex.uv.x < 0.5;
    bool bot_half = from_vertex.uv.y < 0.5;

    vec4 color1 = mixed_texture_val(from_vertex.c1_indices, from_vertex.wang_index, from_vertex.uv);
    vec4 color2 = mixed_texture_val(from_vertex.c2_indices, from_vertex.wang_index, from_vertex.uv);

    vec4 tile_color = mix(
        texture_val((from_vertex.mid_indices >> 0) & 0xff, from_vertex.wang_index, from_vertex.uv),
        texture_val((from_vertex.mid_indices >> 8) & 0xff, from_vertex.wang_index, from_vertex.uv),
        0.5
    );
    vec4 left_center_color = mix(
        texture_val((from_vertex.lr_indices >> 16) & 0xff, from_vertex.wang_index, from_vertex.uv),
        texture_val((from_vertex.lr_indices >> 24) & 0xff, from_vertex.wang_index, from_vertex.uv),
        0.5
    );
    vec4 bot_center_color = mix(
        texture_val((from_vertex.tb_indices >> 0) & 0xff, from_vertex.wang_index, from_vertex.uv),
        texture_val((from_vertex.tb_indices >> 8) & 0xff, from_vertex.wang_index, from_vertex.uv),
        0.5
    );
    vec4 right_center_color = mix(
        texture_val((from_vertex.lr_indices >> 0) & 0xff, from_vertex.wang_index, from_vertex.uv),
        texture_val((from_vertex.lr_indices >> 8) & 0xff, from_vertex.wang_index, from_vertex.uv),
        0.5
    );
    vec4 top_center_color = mix(
        texture_val((from_vertex.tb_indices >> 16) & 0xff, from_vertex.wang_index, from_vertex.uv),
        texture_val((from_vertex.tb_indices >> 24) & 0xff, from_vertex.wang_index, from_vertex.uv),
        0.5
    );

    if(top) {
        if(left_half)
            tex_color = bilinear_interp_vec4(left_center_color, color1, tile_color, top_center_color,
                0.0, 0.5, 0.5, 1.0, from_vertex.uv.x, from_vertex.uv.y);
        else
            tex_color = bilinear_interp_vec4(tile_color, top_center_color, right_center_color, color2,
                0.5, 1.0, 0.5, 1.0, from_vertex.uv.x, from_vertex.uv.y);
    }else if(bot) {
        if(left_half)
            tex_color = bilinear_interp_vec4(color1, left_center_color, bot_center_color, tile_color,
                0.0, 0.5, 0.0, 0.5, from_vertex.uv.x, from_vertex.uv.y);
        else
            tex_color = bilinear_interp_vec4(bot_center_color, tile_color, color2, right_center_color,
                0.5, 1.0, 0.0, 0.5, from_vertex.uv.x, from_vertex.uv.y);
    }else if(left) {
        if(bot_half)
            tex_color = bilinear_interp_vec4(color1, left_center_color, bot_center_color, tile_color,
                0.0, 0.5, 0.0, 0.5, from_vertex.uv.x, from_vertex.uv.y);
        else
            tex_color = bilinear_interp_vec4(left_center_color, color2, tile_color, top_center_color,
                0.0, 0.5, 0.5, 1.0, from_vertex.uv.x, from_vertex.uv.y);
    }else if(right) {
        if(bot_half)
            tex_color = bilinear_interp_vec4(bot_center_color, tile_color, color1, right_center_color,
                0.5, 1.0, 0.0, 0.5, from_vertex.uv.x, from_vertex.uv.y);
        else
            tex_color = bilinear_interp_vec4(tile_color, top_center_color, right_center_color, color2,
                0.5, 1.0, 0.5, 1.0, from_vertex.uv.x, from_vertex.uv.y);
    }else{
        tex_color = tile_color;
    }

    return tex_color;
}

void main()
{
    ivec4 td = tile_desc_at(from_vertex.world_pos);
    float tf = tint_factor(td, from_vertex.uv);

    if(tf == 0.0) {
        o_frag_color = vec4(0.0, 0.0, 0.0, 1.0);
        return;
    }

    vec4 tex_color;
    switch(from_vertex.blend_mode) {
    case BLEND_MODE_NOBLEND:
        tex_color = texture_val(from_vertex.mat_idx, from_vertex.wang_index, from_vertex.uv);
        break;
    case BLEND_MODE_BLUR:
        tex_color = blended_texture_val();
        break;
    default:
        o_frag_color = vec4(1.0, 0.0, 1.0, 1.0);
        return;
    }

    tex_color.rgb *= tex_color.a;
    if(tex_color.a <= 0.5)
        discard;

    float height = from_vertex.world_pos.y / Y_COORDS_PER_TILE;
    vec3 ambient = (TERRAIN_AMBIENT + height * EXTRA_AMBIENT_PER_LEVEL) * ambient_color;

    vec3 normal = normalize(from_vertex.normal);
    vec3 light_dir = normalize(light_pos);
    float diff = max(dot(normal, light_dir), 0.0);
    vec3 diffuse = light_color * (diff * TERRAIN_DIFFUSE);

    vec3 view_dir = normalize(view_pos - from_vertex.world_pos);
    vec3 reflect_dir = reflect(-light_dir, normal);
    float spec = pow(max(dot(view_dir, reflect_dir), 0.0), SPECULAR_SHININESS);
    vec3 specular = SPECULAR_STRENGTH * light_color * (spec * TERRAIN_SPECULAR);

    vec4 final_color = vec4((ambient + diffuse + specular) * tex_color.xyz, 1.0);
    o_frag_color = final_color * tf;
}
