import re
import aiohttp
import asyncio
import json
import traceback
import resources as res
from datetime import datetime


async def run(username, password):
    async with aiohttp.ClientSession() as session:
        data = {
            'client_id': 'play-valorant-web-prod',
            'nonce': '1',
            'redirect_uri': 'https://playvalorant.com/opt_in',
            'response_type': 'token id_token',
        }
        await session.post('https://auth.riotgames.com/api/v1/authorization', json=data)

        data = {
            'type': 'auth',
            'username': username,
            'password': password
        }

        async with session.put('https://auth.riotgames.com/api/v1/authorization', json=data) as r:
            data = await r.json()
        # print(data)
        pattern = re.compile(
            'access_token=((?:[a-zA-Z]|\d|\.|-|_)*).*id_token=((?:[a-zA-Z]|\d|\.|-|_)*).*expires_in=(\d*)')
        data = pattern.findall(data['response']['parameters']['uri'])[0]
        access_token = data[0]
        # print('Access Token: ' + access_token)
        id_token = data[1]
        expires_in = data[2]

        headers = {
            'Authorization': f'Bearer {access_token}',
        }
        async with session.post('https://entitlements.auth.riotgames.com/api/token/v1', headers=headers, json={}) as r:
            data = await r.json()
        entitlements_token = data['entitlements_token']
        # print('Entitlements Token: ' + entitlements_token)

        async with session.post('https://auth.riotgames.com/userinfo', headers=headers, json={}) as r:
            data = await r.json()
        user_id = data['sub']
        # print('User ID: ' + user_id)
        headers['X-Riot-Entitlements-JWT'] = entitlements_token
        await session.close()

        return user_id, headers


async def get_stats(user_id, headers, num_matches=3):

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://pd.na.a.pvp.net/mmr/v1/players/{user_id}/competitiveupdates?startIndex=0&endIndex=20', headers=headers) as r:
                data = json.loads(await r.text())

            matches = data['Matches']
            # print(matches)

            after_points = []
            diff_points = []
            rank_nums = []
            maps = []
            start_times = []
            arrows = []
            curr_matches = []
            count = 0
            for match in matches:
                if (match['CompetitiveMovement'] == 'MOVEMENT_UNKNOWN'):
                    continue
                else:
                    before = match['TierProgressBeforeUpdate']
                    after = match['TierProgressAfterUpdate']
                    after_points.append(after)
                    if (match['CompetitiveMovement'] == 'PROMOTED'):
                        diff = (after - before) + 100
                    elif (match['CompetitiveMovement'] == 'DEMOTED'):
                        diff = (after - before) - 100
                    else:
                        diff = after - before
                    diff_points.append(diff)
                    count += 1
                    rank_nums.append(match['TierAfterUpdate'])
                    maps.append(match['MapID'])
                    arrows.append(match['CompetitiveMovement'])
                    start_time = match['MatchStartTime'] / 1000
                    start_times.append(datetime.fromtimestamp(
                        start_time).strftime('%Y-%m-%d %H:%M'))
                    curr_matches.append(match['MatchID'])

                # [num] recent competitve matches found
                if (count >= num_matches):
                    break

            if (count <= 0):
                return
            else:
                return after_points, diff_points, rank_nums, maps, arrows, start_times, curr_matches

    except:
        print(traceback.format_exc())


async def check(user_id, headers, prev_matches):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://pd.na.a.pvp.net/mmr/v1/players/{user_id}/competitiveupdates?startIndex=0&endIndex=20', headers=headers) as r:
                data = json.loads(await r.text())

            matches = data['Matches']
            curr_matches = []
            count = 0
            for match in matches:
                if (match['CompetitiveMovement'] == 'MOVEMENT_UNKNOWN'):
                    continue
                else:
                    curr_matches.append(match['MatchID'])
                    count += 1

                if (count >= 3):
                    break

            if curr_matches:
                return curr_matches[0] == prev_matches[0]
            else:
                return True
    except:
        print(traceback.format_exc())

if __name__ == '__main__':

    user_id, headers = asyncio.get_event_loop().run_until_complete(
        run('exmaple user name', 'my_secret_password'))
    asyncio.get_event_loop().run_until_complete(get_stats(user_id, headers))
