-- based on https://github.com/DStelter94/ARLinBfW
local helper = wesnoth.require "lua/helper.lua"
local AH = wesnoth.require("ai/lua/ai_helper.lua")
local LS = wesnoth.require "location_set"
local on_event = wesnoth.require("lua/on_event.lua")
-- local re = wesnoth.require("ai/lua/generic_recruit_engine.lua")
local re = wesnoth.require("~/add-ons/PythonRLAddon/lua/recruit.lua")

local recruit_ca = {}
re.init(recruit_ca, {})

local ca_python = {}

local ai_side

math.randomseed( os.time() + os.clock() * 1000)

-- send gs and as to python, then wait the action
-- https://wiki.wesnoth.org/Creating_Custom_AIs#Evaluation_Function
function ca_python:evaluation(cfg, data)
    local units = {}
    ai_side = ai.side
    -- game starting, synchronize with python
    if (wml.variables.ai_input_path == nil) then
        on_event("scenario_end", function(context)
            local win = #(wesnoth.get_units({ side = ai_side, canrecruit = true })) > 0
            print_game_state()
            local result
            if win then
                result = '"victory"'
            else
                result = '"defeated"'
            end
            std_print('[game-result]' .. array_to_json_string( { result = result, playing_side = wesnoth.current.side }, true, false ) )
        end)
        init_and_wait_for_input_file_creation()

        -- print_game_state()

        wml.variables.action_id = -1
    end

    for index, unit in ipairs(wesnoth.get_units({ side = ai_side })) do
        if unit.moves > 0 then
            table.insert(units, get_unit_json(unit, true))
        end
    end
    if next(units, nil) == nil then -- no more units to move
        return 0
    end

    print_game_state()

    std_print('[units-to-move]' .. array_to_json_string(units, false,  true))

    -- debug("waiting action")
    local unit_x, unit_y, action_type, action_x, action_y, action_extra, action_id = read_action_from_input_file()
    --local unit_x, unit_y, action_type, action_x, action_y, action_extra, action_id = wesnoth.dofile(wml.variables.ai_input_path)
    --while (action_id == nil or unit_x == nil or unit_x == -1 or action_id == wml.variables.action_id) do
    --    unit_x, unit_y, action_type, action_x, action_y, action_extra, action_id = wesnoth.dofile(wml.variables.ai_input_path)
    --end
    -- debug("action received")
    wml.variables.action_id = action_id

    data['action'] = {unit={x=unit_x, y=unit_y}, action_type=action_type, action_x=action_x, action_y=action_y, action_id=action_id, action_extra=action_extra}

     -- debug('end eval')
    return 999990
end

-- executes the action writen in input file
-- https://wiki.wesnoth.org/Creating_Custom_AIs#Execution_Function
-- https://wiki.wesnoth.org/LuaAI#ai_Table_Functions_for_Executing_AI_Moves
function ca_python:execution(cfg, data)
    local unit = wesnoth.get_unit(data['action'].unit.x, data['action'].unit.y)
    -- std_print(dump(data['action']))
    if data['action'].action_id ~= -1 then
        if data['action'].action_type == 'move' then
            if unit.x~= data['action'].action_x or unit.y~=data['action'].action_y then
                ai.move_full(unit, data['action'].action_x, data['action'].action_y)
            else
                ai.stopunit_moves(unit)
            end
            --unit = wesnoth.get_unit(data['action'].action_x, data['action'].action_y)
            --ai.stopunit_moves(unit)
        elseif data['action'].action_type == 'attack' then
            --local check = ai.check_move(unit, data['action'].action_x, data['action'].action_y)
            --std_print('[debug] attacking from x=' .. unit.x .. ', y=' .. unit.y .. ' to x=' .. data['action'].action_x .. ', y=' .. data['action'].action_y .. ' attacks left=' .. unit.attacks_left .. ' moves left=' .. unit.moves .. ' status=' .. tostring(check.ok) )
            if unit.x~= data['action'].action_x or unit.y~=data['action'].action_y then
                ai.move_full(unit, data['action'].action_x, data['action'].action_y)
                unit = wesnoth.get_unit(data['action'].action_x, data['action'].action_y)
            end
            enemy = wesnoth.get_unit(data['action'].action_extra.target_x, data['action'].action_extra.target_y)
            local weapon = data['action'].action_extra.weapon
            if weapon == 'best' then
                local att_stats, def_stats, att_weapon = wesnoth.simulate_combat(unit, enemy)
                weapon = att_weapon.name
            end
            local check = ai.attack(unit, enemy, weapon)
            --std_print(dump(check))
        elseif data['action'].action_type == 'recruit' then
            if unit.x~= data['action'].action_x or unit.y~=data['action'].action_y then
                ai.move_full(unit, data['action'].action_x, data['action'].action_y)
                unit = wesnoth.get_unit(data['action'].action_x, data['action'].action_y)
            end
            rec_type = data['action'].action_extra.recruit_type
            if rec_type == 'best' then
                local pre_recruit_units_count = 0
                local post_recruit_units_count = pre_recruit_units_count + 1
                while recruit_ca:recruit_rushers_eval() > 0 and post_recruit_units_count > pre_recruit_units_count do
                    -- debug('recruit eval ' .. recruit_ca:recruit_rushers_eval())
                    pre_recruit_units_count = #(wesnoth.get_units({ side = ai_side}))
                    recruit_ca:recruit_rushers_exec()
                    post_recruit_units_count = #(wesnoth.get_units({ side = ai_side}))
                end
            else
                local check = AH.checked_recruit(ai, rec_type)
                --std_print(dump(check))
            end
        end
    end
end

function read_action_from_input_file()
    local unit_x, unit_y, action_type, action_x, action_y, action_extra, action_id
    while (action_id == nil or unit_x == nil or unit_x == -1 or action_id == wml.variables.action_id) do
        pcall(function ()
            unit_x, unit_y, action_type, action_x, action_y, action_extra, action_id = wesnoth.dofile(wml.variables.ai_input_path)
        end)
    end
    return unit_x, unit_y, action_type, action_x, action_y, action_extra, action_id
end

function print_game_state()
    std_print('[game-state]' .. get_game_state_json())
end

function get_game_state_json()
    local map_width, map_height, map_border = wesnoth.get_map_size()
    local turn_limit = wesnoth.game_config.last_turn
    local finished = wesnoth.current.turn == turn_limit
    local side = wesnoth.sides[ai_side]

    local json_state = {
        map = {
            width = map_width,
            height = map_height,
            border = map_border,
            time = '"' .. wesnoth.get_time_of_day().id .. '"',
            villages_count = #(wesnoth.get_villages({})),
            villages = get_villages_json(),
            units = get_units_json(),
            terrain = get_terrain_json(map_width),
        },
        turn = {
            current= wesnoth.current.turn,
            limit= turn_limit
        },
        game = {
            finished = tostring(finished),
            limit = wesnoth.game_config.last_turn,
            unit_types = array_to_json_string(get_unit_types(), false, false)
        },
        own= {
            side = ai_side,
            gold = wesnoth.game_config.last_turn,
            villages_count = side.num_villages,
            units_count = #(wesnoth.get_units({ side = ai_side}))
        },
    }
    return array_to_json_string(json_state, true,  true)
end

function get_unit_types()
    local unit_types ={}
    for _,side in ipairs(wesnoth.sides) do
        for _,recruit_type in ipairs(side.recruit) do
            unit_types[recruit_type]= '"' .. recruit_type .. '"'
            for _, a in ipairs( get_advancements(recruit_type) ) do
                unit_types[a] = '"' .. a .. '"'
            end
        end
    end
    local newtbl = {}
    for s,c in pairs(unit_types) do
      table.insert(newtbl,c)
    end
    return newtbl
end

function get_advancements(unit_type)
    local u = wesnoth.create_unit { type = unit_type, gender = "female" }
    local advancements = {}
    for _, advancement_type in ipairs(u.advances_to) do
        table.insert(advancements,advancement_type)
        for _, a in ipairs( get_advancements(advancement_type) ) do
            table.insert(advancements, a)
        end
    end
    return advancements
end

function array_to_json_string(arr, root_is_object, content_is_object)
    local s = ""
    local c = ""

    for k, v in next, arr do
        if root_is_object then
            s = s .. "\"" ..k .. "\": "
        end

        if content_is_object then
            c = "{"
            for vk, vv in next, v do
                c = c .. "\"" ..vk .. "\" : " .. vv
                if next(v, vk) ~= nil then
                    c = c .. ", "
                end
            end
            c = c .. "}"
        else
            c = v
        end

        s = s .. c
        if next(arr, k) ~= nil then
            s = s .. ", "
        end

    end

    if root_is_object then
        s = "{" .. s .."}"
    else
        s = "[" .. s .."]"
    end

    return s
end

function get_villages_json()
    local villages = {}
    for index, village in ipairs(wesnoth.get_villages({})) do
        local owner = wesnoth.get_village_owner(village[1], village[2])
        if (owner) then
            if (ai_side == owner) then
                owner = 1
            else
                owner = 2
            end
        else
            owner = 0
        end
        villages[index] = {
            x = village[1],
            y = village[2],
            owner = owner
        }
    end
    return array_to_json_string(villages, false, true)
end

function get_units_json()
    local units = {}
    for index, unit in ipairs(wesnoth.get_units({})) do
        if (ai_side == unit.side) then
            owner = 1
        else
            owner = 2
        end
        units[index] = get_unit_json(unit, false)
    end
    return array_to_json_string(units, false, true)
end

function get_unit_json(unit, with_moves)
    if (ai_side == unit.side) then
        owner = 1
    else
        owner = 2
    end

    local unit = {
        x = unit.x,
        y = unit.y,
        id = '"' .. unit.id .. '"',
        type = '"' .. unit.type .. '"',
        name = '"' .. unit.name .. '"',
        max_hitpoints = unit.max_hitpoints,
        hitpoints = unit.hitpoints,
        max_moves = unit.max_moves,
        max_attacks = unit.max_attacks,
        attacks_left = unit.attacks_left,
        moves = unit.moves,
        level = unit.level,
        resting = tostring(unit.resting),
        hidden = tostring(unit.hidden),
        petrified = tostring(unit.petrified),
        canrecruit = tostring(unit.canrecruit),
        owner = owner
    }

    if with_moves then
        unit.possible_moves = get_unit_possible_moves_json(unit)
    else
        possible_moves = {}
    end

    return unit
end

function get_unit_possible_moves_json(unit)
    local moves = {}
    local t = wesnoth.find_reach(unit, {})
    unit = wesnoth.get_unit(unit.x, unit.y)

    for i,l in ipairs(t) do
        local check = ai.check_move(unit, l[1], l[2])
        local is_empty = wesnoth.get_unit(l[1], l[2]) == nil
        if ((is_empty and check.ok) or (unit.x == l[1] and unit.y == l[2])) then
            table.insert(moves, {
                type='"move"',
                x= l[1],
                y= l[2],
            })
            -- attack actions
            if unit.attacks_left > 0 then
                local attacker_copy = wesnoth.copy_unit(unit)
                for x, y in helper.adjacent_tiles(l[1], l[2]) do
                    local enemy = wesnoth.get_unit(x, y)
                    if (enemy and wesnoth.is_enemy(enemy.side, ai_side)) then
                        --for weapon_number,att in ipairs(unit.attacks) do
                        --    table.insert(moves, {
                        --        type='"attack"',
                        --        x= l[1],
                        --        y= l[2],
                        --        attack_name ='"' .. att.name ..'"',
                        --        target_x= x,
                        --        target_y= y,
                        --        target_leader = tostring(enemy.canrecruit),
                        --        target_hp = enemy.hitpoints,
                        --        target_max_hp = enemy.max_hitpoints
                        --    })
                        --end
                        attacker_copy.x = l[1]
                        attacker_copy.y = l[2]
                        local att_stats, def_stats, att_weapon = wesnoth.simulate_combat(attacker_copy, enemy)
                        table.insert(moves, {
                            type='"attack"',
                            x= l[1],
                            y= l[2],
                            attack_name ='"best"',
                            target_x= x,
                            target_y= y,
                            unit_new_hp = att_stats.average_hp,
                            target_leader = tostring(enemy.canrecruit),
                            target_hp = enemy.hitpoints,
                            target_new_hp = def_stats.average_hp,
                            target_max_hp = enemy.max_hitpoints
                        })
                    end
                end
            end
            --recruit
            if can_recruit(unit, l[1], l[2]) then
                local leader_copy = wesnoth.copy_unit(unit)
                leader_copy.x = l[1]
                leader_copy.y = l[2]
                -- local can_recruit = false
                -- for _,recruit_type in ipairs(wesnoth.sides[wesnoth.current.side].recruit) do
                --     if wesnoth.unit_types[recruit_type].cost <= wesnoth.sides[wesnoth.current.side].gold then
                --         can_recruit=true
                        --table.insert(moves, {
                        --    type='"recruit"',
                        --    x= l[1],
                        --    y= l[2],
                        --    recruit_type='"'..recruit_type..'"',
                        --    recruit_cost=wesnoth.unit_types[recruit_type].cost
                        --})
                --     end
                -- end
                -- if can_recruit then
                if recruit_ca:recruit_rushers_eval(leader_copy) > 0 then
                    table.insert(moves, {
                        type='"recruit"',
                        x= l[1],
                        y= l[2],
                        recruit_type='"best"',
                        recruit_cost=-1
                    })
                end
            end
        end
    end

    return array_to_json_string(moves, false, true)
end

function can_recruit(leader, leader_x, leader_y)
    -- local leader = wesnoth.get_units { side = wesnoth.current.side, canrecruit = 'yes' }[1]
    if (leader.canrecruit == false) or (not wesnoth.get_terrain_info(wesnoth.get_terrain(leader_x, leader_y)).keep) then
        return false
    end

    local empty_castle = find_empty_castle(leader_x, leader_y):filter(function(x, y)
      return x ~= leader_x or y ~= leader_y
    end)

    -- std_print('------------- empty castle' .. leader.name)
    -- std_print(dump({leader_x, leader_y}))
    -- std_print(dump(empty_castle:to_pairs()))

    return not empty_castle:empty()

    -- Check if there is space left for recruiting
    -- local no_space = true
    -- castle_map:iter(function(x, y)
    --     local unit = wesnoth.get_unit(x, y)
    --     if (not unit) then
    --         no_space = false
    --     end
    -- end)
    -- return not no_space
end

function find_empty_castle(leader_x, leader_y)
    -- Find all connected castle hexes
    local castle_map = LS.of_pairs({ { leader_x, leader_y } })
    local width, height, border = wesnoth.get_map_size()
    local new_castle_hex_found = true

    while new_castle_hex_found do
        new_castle_hex_found = false
        local new_hexes = {}

        castle_map:iter(function(x, y)
            for xa,ya in helper.adjacent_tiles(x, y) do
                if (not castle_map:get(xa, ya))
                    and (xa >= 1) and (xa <= width)
                    and (ya >= 1) and (ya <= height)
                then
                    local is_castle = wesnoth.get_terrain_info(wesnoth.get_terrain(xa, ya)).castle

                    if is_castle then
                        table.insert(new_hexes, { xa, ya })
                        new_castle_hex_found = true
                    end
                end
            end
        end)

        for _,hex in ipairs(new_hexes) do
            castle_map:insert(hex[1], hex[2])
        end
    end

    return castle_map:filter(function(x, y)
        return wesnoth.get_unit(x, y) == nil
    end)
end

function debug(str)
    std_print('[debug]' .. str)
end

function dump(o)
    if type(o) == 'table' then
        local s = '{ '
        for k,v in pairs(o) do
                if type(k) ~= 'number' then k = '"'..k..'"' end
                s = s .. '['..k..'] = ' .. dump(v) .. ','
        end
        return s .. '} '
    else
        return tostring(o)
    end
end

function getTableKeys(tab)
  local keyset = {}
  for k,v in pairs(tab) do
    keyset[#keyset + 1] = k
  end
  return keyset
end

function log(text)
    std_print('[input-file]' .. text)
end

-- https://github.com/DStelter94/ARLinBfW
function get_terrain_json(w)
    local map = {}
    for i=1,w do
        map[i] = {}
    end
    for index, location in ipairs(wesnoth.get_locations({include_borders = false})) do
        map[location[1]][location[2]] = '"' .. wesnoth.get_terrain(location[1], location[2]) .. '"'
    end
    for i=1,w do
        map[i] = array_to_json_string(map[i], false, false)
    end
    return array_to_json_string(map, false, false)
end

-- https://github.com/DStelter94/ARLinBfW
-- generate random input file name and wait for its creation
function init_and_wait_for_input_file_creation() 
    local uuid = uuid()
    wml.variables.ai_input_path = "~/input/" .. uuid .. ".lua"

	-- send filename to python
    std_print('[input-file]' .. wml.variables.ai_input_path)

    local map_width, map_height, map_border = wesnoth.get_map_size()
    local json_config = {
        map_width = map_width,
        map_height = map_height,
    }
    std_print('[game-config]' .. array_to_json_string(json_config, true,  false))

	--wait python create file
    while (not wesnoth.have_file(wml.variables.ai_input_path)) do
    end
end

-- https://github.com/DStelter94/ARLinBfW
-- generates a random uuid
-- https://gist.github.com/jrus/3197011
function uuid()
    local template ='xxxxxxxxxx'
    return string.gsub(template, '[xy]', function (c)
        local v = (c == 'x') and math.random(0, 0xf) or math.random(8, 0xb)
        return string.format('%x', v)
    end)
end


return ca_python