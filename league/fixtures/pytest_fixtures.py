import datetime
import pytz

import pytest

from league import models


@pytest.fixture()
def league_event():
    dt = datetime.datetime.min.replace(tzinfo=pytz.utc)
    return models.LeagueEvent.objects.create(begin_time=dt, end_time=dt)


@pytest.fixture()
def registry(league_event):
    models.Registry.objects.create(
        pk=1,
        primary_event=league_event,
    )


@pytest.fixture()
def cho_chikun():
    user = models.User.objects.create(
        username="cho_chikun",
    )
    models.Profile.objects.create(
        ogs_id=11,
        user=user,
    )
    return user


@pytest.fixture()
def kobayashi_koichi():
    user = models.User.objects.create(
        username="kobayashi_koichi",
    )
    models.Profile.objects.create(
        ogs_id=22,
        user=user,
    )
    return user


@pytest.fixture()
def sgf_cho_vs_kobayashi(cho_chikun, kobayashi_koichi, league_event):
    sgf = models.Sgf.objects.create(
        date=datetime.datetime.now(),
        league_valid=True,
        white=cho_chikun,
        black=kobayashi_koichi,
        winner=cho_chikun,
    )
    sgf.events.set([league_event])
    return sgf


@pytest.fixture(scope="session")
def sgf_text():
    return '''(;GM[1]FF[4]CA[UTF-8]AP[CGoban:3]ST[2]
    RU[Japanese]SZ[19]KM[0.50]TM[60]OT[1x10 byo-yomi]
    PW[climu]PB[nomenest]WR[1k]BR[2k]DT[2016-11-19]PC[The KGS Go Server at http://www.gokgs.com/]RE[W+36.50]
    ;B[pd]BL[58.365]C[climu [1k\\]: hi
    nomenest [2k\\]: hi
    climu [1k\\]: hf#OSR
    ]
    ;W[dp]WL[55.      342]
    ;B[pp]BL[57.538]
    ;W[dc]WL[53.277]
    ;B[jd]BL[54.617]
    ;W[nq]WL[49.771]
    ;B[np]BL[53.048]
    ;W[mp]WL[47.85]
    ;B[oq]BL[51.884]
    ;W[no]WL[46.413]
    ;       B[op]BL[51.292]
    ;W[mq]WL[45.626]
    ;B[mo]BL[50.229]
    ;W[lo]WL[42.752]
    ;B[mn]BL[49.006]
    ;W[ln]WL[40.421]
    ;B[nn]BL[47.845]
    ;W[gq]WL[38.03]
    ;B[ip]BL[45.     869]
    ;W[in]WL[32.117]
    ;B[gp]BL[44.085]
    ;W[fq]WL[29.957]
    ;B[fp]BL[42.691]
    ;W[ep]WL[26.917]
    ;B[fm]BL[40.689]
    ;W[fo]WL[10]OW[1]
    ;B[go]BL[38.516]
    ;     W[gn]WL[10]OW[1]
    ;B[fn]BL[36.818]
    ;W[eo]WL[10]OW[1]
    ;B[hn]BL[35.99]
    ;W[gm]WL[10]OW[1]
    ;B[hm]BL[35.292]
    ;W[gl]WL[10]OW[1]
    ;B[io]BL[33.764]
    ;            W[fl]WL[10]OW[1]
    ;B[jn]BL[31.562]
    ;W[lm]WL[10]OW[1]
    ;B[qm]BL[28.422]
    ;W[on]WL[10]OW[1]
    ;B[om]BL[23.368]
    ;W[nm]WL[10]OW[1]
    ;B[oo]BL[21.88]
    ;            W[mm]WL[10]OW[1]
    ;B[pn]BL[21.269]
    ;W[hl]WL[10]OW[1]
    ;B[im]BL[19.47]
    ;W[kq]WL[10]OW[1]
    ;B[cq]BL[17.041]
    ;W[cp]WL[10]OW[1]
    ;B[bp]BL[14.061]
    ;            W[bo]WL[10]OW[1]
    ;B[br]BL[12.433]
    ;W[dr]WL[10]OW[1]
    ;B[dq]BL[10.383]
    ;W[eq]WL[10]OW[1]
    ;B[cr]BL[9.645]
    ;W[ap]WL[10]OW[1]
    ;B[er]BL[7.797]
    ;             W[ce]WL[10]OW[1]
    ;B[ch]BL[5.553]
    ;W[cj]WL[10]OW[1]
    ;B[cf]BL[4.003]
    ;W[de]WL[10]OW[1]
    ;B[dj]BL[2.06]
    ;W[dk]WL[10]OW[1]
    ;B[di]BL[0.952]
    ;                W[ek]WL[10]OW[1]
    ;B[be]BL[10]OB[1]
    ;W[bd]WL[10]OW[1]
    ;B[bg]BL[10]OB[1]
    ;W[ae]WL[10]OW[1]
    ;B[af]BL[10]OB[1]
    ;W[bf]WL[10]OW[1]
    ;B[bi]BL[10]OB[1]
    ;       W[ag]WL[10]OW[1]
    ;B[bj]BL[10]OB[1]
    ;W[bk]WL[10]OW[1]
    ;B[df]BL[10]OB[1]
    ;W[ef]WL[10]OW[1]
    ;B[eg]BL[10]OB[1]
    ;W[fg]WL[10]OW[1]
    ;B[ff]BL[10]OB[1]
    ;       W[ee]WL[10]OW[1]
    ;B[eh]BL[10]OB[1]
    ;W[dg]WL[10]OW[1]
    ;B[cg]BL[10]OB[1]
    ;W[gf]WL[10]OW[1]
    ;B[fh]BL[10]OB[1]
    ;W[fe]WL[10]OW[1]
    ;B[fj]BL[10]OB[1]
    ;       W[ej]WL[10]OW[1]
    ;B[ei]BL[10]OB[1]
    ;W[gh]WL[10]OW[1]
    ;B[gi]BL[10]OB[1]
    ;W[hh]WL[10]OW[1]
    ;B[hi]BL[10]OB[1]
    ;W[il]WL[10]OW[1]
    ;B[jl]BL[10]OB[1]
    ;       W[jk]WL[10]OW[1]
    ;B[hq]BL[10]OB[1]
    ;W[ii]WL[10]OW[1]
    ;B[ah]BL[10]OB[1]
    ;W[aj]WL[10]OW[1]
    ;B[af]BL[10]OB[1]
    ;W[fr]WL[10]OW[1]
    ;B[ds]BL[10]OB[1]
    ;       W[ag]WL[10]OW[1]
    ;B[ck]BL[10]OB[1]
    ;W[cl]WL[10]OW[1]
    ;B[af]BL[10]OB[1]
    ;W[kl]WL[10]OW[1]
    ;B[be]BL[10]OB[1]
    ;W[jq]WL[10]OW[1]
    ;B[iq]BL[10]OB[1]
    ;       W[bf]WL[10]OW[1]
    ;B[ag]BL[10]OB[1]
    ;W[nc]WL[10]OW[1]
    ;B[gc]BL[10]OB[1]
    ;W[qf]WL[10]OW[1]
    ;B[oe]BL[10]OB[1]
    ;W[qc]WL[10]OW[1]
    ;B[pc]BL[10]OB[1]
    ;       W[qd]WL[10]OW[1]
    ;B[pf]BL[10]OB[1]
    ;W[qg]WL[10]OW[1]
    ;B[qb]BL[10]OB[1]
    ;W[rb]WL[10]OW[1]
    ;B[pb]BL[10]OB[1]
    ;W[kd]WL[10]OW[1]
    ;B[ke]BL[10]OB[1]
    ;       W[jc]WL[10]OW[1]
    ;B[kc]BL[10]OB[1]
    ;W[ld]WL[10]OW[1]
    ;B[ic]BL[10]OB[1]
    ;W[je]WL[10]OW[1]
    ;B[jb]BL[10]OB[1]
    ;W[le]WL[10]OW[1]
    ;B[kf]BL[10]OB[1]
    ;       W[lf]WL[10]OW[1]
    ;B[ie]BL[10]OB[1]
    ;W[kg]WL[10]OW[1]
    ;B[jf]BL[10]OB[1]
    ;W[pg]WL[10]OW[1]
    ;B[og]BL[10]OB[1]
    ;W[oh]WL[10]OW[1]
    ;B[ng]BL[10]OB[1]
    ;       W[lh]WL[10]OW[1]
    ;B[nh]BL[10]OB[1]
    ;W[oi]WL[10]OW[1]
    ;B[mc]BL[10]OB[1]
    ;W[lc]WL[10]OW[1]
    ;B[mb]BL[10]OB[1]
    ;W[kb]WL[10]OW[1]
    ;B[lb]BL[10]OB[1]
    ;       W[jc]WL[10]OW[1]
    ;B[qe]BL[10]OB[1]
    ;W[re]WL[10]OW[1]
    ;B[kc]BL[10]OB[1]
    ;W[pe]WL[10]OW[1]
    ;B[ka]BL[10]OB[1]
    ;W[of]WL[10]OW[1]
    ;B[ne]BL[10]OB[1]
    ;       W[qk]WL[10]OW[1]
    ;B[rl]BL[10]OB[1]
    ;W[jm]WL[10]OW[1]
    ;B[eb]BL[10]OB[1]
    ;W[jo]WL[10]OW[1]
    ;B[jr]BL[10]OB[1]
    ;W[kr]WL[10]OW[1]
    ;B[hr]BL[10]OB[1]
    ;       W[fs]WL[10]OW[1]
    ;B[is]BL[10]OB[1]
    ;W[ks]WL[10]OW[1]
    ;B[js]BL[10]OB[1]
    ;W[es]WL[10]OW[1]
    ;B[aq]BL[10]OB[1]
    ;W[bq]WL[10]OW[1]
    ;B[db]BL[10]OB[1]
    ;       W[ar]WL[10]OW[1]
    ;B[cc]BL[10]OB[1]
    ;W[cd]WL[10]OW[1]
    ;B[bc]BL[10]OB[1]
    ;W[rk]WL[10]OW[1]
    ;B[or]BL[10]OB[1]
    ;W[ql]WL[10]OW[1]
    ;B[rm]BL[10]OB[1]
    ;       W[ni]WL[10]OW[1]
    ;B[nf]BL[10]OB[1]
    ;W[ol]WL[10]OW[1]
    ;B[mh]BL[10]OB[1]
    ;W[mi]WL[10]OW[1]
    ;B[ij]BL[10]OB[1]
    ;W[jj]WL[10]OW[1]
    ;B[ih]BL[10]OB[1]
    ;       W[ji]WL[10]OW[1]
    ;B[ig]BL[10]OB[1]
    ;W[ec]WL[10]OW[1]
    ;B[fc]BL[10]OB[1]
    ;W[hf]WL[10]OW[1]
    ;B[hj]BL[10]OB[1]
    ;W[hg]WL[10]OW[1]
    ;B[jp]BL[10]OB[1]
    ;       W[ko]WL[10]OW[1]
    ;B[kp]BL[10]OB[1]
    ;W[lp]WL[10]OW[1]
    ;B[nr]BL[10]OB[1]
    ;W[mr]WL[10]OW[1]
    ;B[fd]BL[10]OB[1]
    ;W[ed]WL[10]OW[1]
    ;B[hd]BL[10]OB[1]
    ;       W[ac]WL[10]OW[1]
    ;B[ab]BL[10]OB[1]
    ;W[bb]WL[10]OW[1]
    ;B[ad]BL[10]OB[1]
    ;W[md]WL[10]OW[1]
    ;B[nd]BL[10]OB[1]
    ;W[ac]WL[10]OW[1]
    ;B[cb]BL[10]OB[1]
    ;       W[aa]WL[10]OW[1]
    ;B[be]BL[10]OB[1]
    ;W[ad]WL[10]OW[1]
    ;B[ge]BL[10]OB[1]
    ;W[ca]WL[10]OW[1]
    ;B[da]BL[10]OB[1]
    ;W[fb]WL[10]OW[1]
    ;B[ba]BL[10]OB[1]
    ;       W[gs]WL[10]OW[1]
    ;B[hs]BL[10]OB[1]
    ;W[ca]WL[10]OW[1]
    ;B[lg]BL[10]OB[1]
    ;W[mg]WL[10]OW[1]
    ;B[ba]BL[10]OB[1]
    ;W[if]WL[10]OW[1]
    ;B[ab]BL[10]OB[1]
    ;       W[jg]WL[10]OW[1]
    ;B[je]BL[10]OB[1]
    ;W[sl]WL[10]OW[1]
    ;B[sm]BL[10]OB[1]
    ;W[sk]WL[10]OW[1]
    ;B[pl]BL[10]OB[1]
    ;W[pk]WL[10]OW[1]
    ;B[he]BL[10]OB[1]
    ;       W[pm]WL[10]OW[1]
    ;B[on]BL[10]OB[1]
    ;W[qn]WL[10]OW[1]
    ;B[rn]BL[10]OB[1]
    ;W[ns]WL[10]OW[1]
    ;B[os]BL[10]OB[1]
    ;W[ms]WL[10]OW[1]
    ;B[pl]BL[10]OB[1]
    ;       W[ra]WL[10]OW[1]
    ;B[qa]BL[10]OB[1]
    ;W[bf]WL[10]OW[1]
    ;B[ai]BL[10]OB[1]
    ;W[ak]WL[10]OW[1]
    ;B[pm]BL[10]OB[1]
    ;W[ck]WL[10]OW[1]
    ;B[ci]BL[10]OB[1]
    ;       W[fk]WL[10]OW[1]
    ;B[pf]BL[10]OB[1]
    ;W[qe]WL[10]OW[1]
    ;B[of]BL[10]OB[1]
    ;W[kn]WL[10]OW[1]
    ;B[in]BL[10]OB[1]
    ;W[lg]WL[10]OW[1]
    ;B[oc]BL[10]OB[1]
    ;       W[me]WL[10]OW[1]
    ;B[nb]BL[10]OB[1]
    ;W[]WL[10]OW[1]
    ;                                                                                                                  B[]BL[10]OB[1]TW[sa][sb][rc][sc][dd][rd][sd][se][ff][rf][sf][gg][ig][rg][sg][ih][jh][kh][ph][qh][rh][sh][ki][li][pi][qi][ri][si][kj][lj][mj][nj][oj][pj][qj][rj][sj][kk][lk][mk][nk][ok][al][bl][dl][el][jl][ll][ml][nl][am][bm][cm][dm][em][fm][km][an][bn][cn][dn][en][fn][ao][co][do][bp][aq][cq][dq][lq][br][cr][dr][er][lr][as][bs][cs][ds][ls]TB[aa][ca][ea][fa][ga][ha][ia][ja][la][ma][na][oa][pa][bb][fb][gb][hb][ib][kb][ob][hc][jc][nc][gd][id][od][qn][sn][ho][no][po][qo][ro][so][hp][qp][rp][sp][pq][qq][rq][sq][ir][pr][qr][rr][sr][ps][qs][rs][ss]C[climu [1k\\]: ty
    nomenest [2k\\]: thx
    ])'''


@pytest.fixture(scope="session")
def ogs_response():
    return {
        "count": 95,
        "next": None,
        "previous": None,
        "results": [
            {
                "related": {
                    "detail": "/api/v1/games/16083413"
                },
                "players": {
                    "black": {
                        "id": 531928,
                        "username": "Naxe",
                        "country": "ru",
                        "icon": "https://b0c2ddc39d13e1c0ddad-93a52a5bc9e7cc06050c1a999beb3694.ssl.cf1.rackcdn.com/8b76b3356a7f05669ea9fbeb28b2a05d-32.png",
                        "ratings": {
                            "overall": {
                                "deviation": 84.52931783075007,
                                "rating": 1760.5976721537445,
                                "games_played": 169,
                                "volatility": 0.06097800395022088
                            }
                        },
                        "ranking": 20,
                        "professional": False,
                        "ui_class": ""
                    },
                    "white": {
                        "id": 106155,
                        "username": "raylu",
                        "country": "_Pirate",
                        "icon": "https://b0c2ddc39d13e1c0ddad-93a52a5bc9e7cc06050c1a999beb3694.ssl.cf1.rackcdn.com/2b733fc955a2883ef8a7093ff10563f5-32.png",
                        "ratings": {
                            "overall": {
                                "deviation": 119.06634171319544,
                                "rating": 1626.0943874056077,
                                "games_played": 30,
                                "volatility": 0.05991960465200883
                            }
                        },
                        "ranking": 17,
                        "professional": False,
                        "ui_class": "supporter"
                    }
                },
                "id": 16083413,
                "name": "Tournament Game: Correspondence Weekly McMahon 19x19 2018-06-09 17:00 (37872) R:2 (raylu vs Naxe)",
                "creator": 106155,
                "mode": "game",
                "source": "play",
                "black": 531928,
                "white": 106155,
                "width": 19,
                "height": 19,
                "rules": "japanese",
                "ranked": True,
                "handicap": 0,
                "komi": "6.50",
                "time_control": "simple",
                "black_player_rank": 21,
                "black_player_rating": "1204.883",
                "white_player_rank": 17,
                "white_player_rating": "854.912",
                "time_per_move": 89280,
                "time_control_parameters": "{\"time_control\": \"fischer\", \"initial_time\": 259200, \"pause_on_weekends\": true, \"max_time\": 259200, \"time_increment\": 86400}",
                "disable_analysis": False,
                "tournament": 37872,
                "tournament_round": 2,
                "ladder": None,
                "pause_on_weekends": True,
                "outcome": "Resignation",
                "black_lost": False,
                "white_lost": True,
                "annulled": False,
                "started": "2019-01-11T03:46:34.078273-05:00",
                "ended": "2019-04-30T14:41:18.183258-04:00",
                "sgf_filename": None,
                "historical_ratings": {
                    "black": {
                        "id": 531928,
                        "ratings": {
                            "overall": {
                                "rating": 1771.5311279296875,
                                "deviation": 90.05663299560547,
                                "volatility": 0.061021242290735245
                            }
                        },
                        "username": "Naxe",
                        "country": "Naxe",
                        "ranking": 20,
                        "professional": False,
                        "icon": "https://b0c2ddc39d13e1c0ddad-93a52a5bc9e7cc06050c1a999beb3694.ssl.cf1.rackcdn.com/8b76b3356a7f05669ea9fbeb28b2a05d-32.png",
                        "ui_class": ""
                    },
                    "white": {
                        "id": 106155,
                        "ratings": {
                            "overall": {
                                "rating": 1652.8897705078125,
                                "deviation": 109.97587585449219,
                                "volatility": 0.05992735177278519
                            }
                        },
                        "username": "raylu",
                        "country": "raylu",
                        "ranking": 17,
                        "professional": False,
                        "icon": "https://b0c2ddc39d13e1c0ddad-93a52a5bc9e7cc06050c1a999beb3694.ssl.cf1.rackcdn.com/2b733fc955a2883ef8a7093ff10563f5-32.png",
                        "ui_class": "supporter"
                    }
                }
            },
            {
                "related": {
                    "detail": "/api/v1/games/16963628"
                },
                "players": {
                    "black": {
                        "id": 610746,
                        "username": "stonemuncher",
                        "country": "gb",
                        "icon": "https://b0c2ddc39d13e1c0ddad-93a52a5bc9e7cc06050c1a999beb3694.ssl.cf1.rackcdn.com/c8ec4f3f96c64417c12e6e7b7c57a63d-32.png",
                        "ratings": {
                            "overall": {
                                "deviation": 91.68388954461214,
                                "rating": 1736.140415330084,
                                "games_played": 42,
                                "volatility": 0.060318472835717056
                            }
                        },
                        "ranking": 18,
                        "professional": False,
                        "ui_class": ""
                    },
                    "white": {
                        "id": 106155,
                        "username": "raylu",
                        "country": "_Pirate",
                        "icon": "https://b0c2ddc39d13e1c0ddad-93a52a5bc9e7cc06050c1a999beb3694.ssl.cf1.rackcdn.com/2b733fc955a2883ef8a7093ff10563f5-32.png",
                        "ratings": {
                            "overall": {
                                "deviation": 119.06634171319544,
                                "rating": 1626.0943874056077,
                                "games_played": 30,
                                "volatility": 0.05991960465200883
                            }
                        },
                        "ranking": 17,
                        "professional": False,
                        "ui_class": "supporter"
                    }
                },
                "id": 16963628,
                "name": "Friendly Match",
                "creator": 106155,
                "mode": "game",
                "source": "play",
                "black": 610746,
                "white": 106155,
                "width": 19,
                "height": 19,
                "rules": "japanese",
                "ranked": True,
                "handicap": 0,
                "komi": "6.50",
                "time_control": "fischer",
                "black_player_rank": 14,
                "black_player_rating": "572.976",
                "white_player_rank": 18,
                "white_player_rating": "915.978",
                "time_per_move": 89280,
                "time_control_parameters": "{\"system\": \"fischer\", \"pause_on_weekends\": true, \"time_control\": \"fischer\", \"initial_time\": 259200, \"max_time\": 432000, \"time_increment\": 86400, \"speed\": \"correspondence\"}",
                "disable_analysis": True,
                "tournament": None,
                "tournament_round": 0,
                "ladder": None,
                "pause_on_weekends": True,
                "outcome": "Resignation",
                "black_lost": False,
                "white_lost": True,
                "annulled": False,
                "started": "2019-03-12T16:19:12.801090-04:00",
                "ended": "2019-04-23T13:42:39.151854-04:00",
                "sgf_filename": None,
                "historical_ratings": {
                    "black": {
                        "id": 610746,
                        "ratings": {
                            "overall": {
                                "rating": 1699.94482421875,
                                "deviation": 76.8810806274414,
                                "volatility": 0.06031230464577675
                            }
                        },
                        "username": "stonemuncher",
                        "country": "stonemuncher",
                        "ranking": 18,
                        "professional": False,
                        "icon": "https://b0c2ddc39d13e1c0ddad-93a52a5bc9e7cc06050c1a999beb3694.ssl.cf1.rackcdn.com/c8ec4f3f96c64417c12e6e7b7c57a63d-32.png",
                        "ui_class": ""
                    },
                    "white": {
                        "id": 106155,
                        "ratings": {
                            "overall": {
                                "rating": 1689.1734619140625,
                                "deviation": 115.30014038085938,
                                "volatility": 0.05995921045541763
                            }
                        },
                        "username": "raylu",
                        "country": "raylu",
                        "ranking": 17,
                        "professional": False,
                        "icon": "https://b0c2ddc39d13e1c0ddad-93a52a5bc9e7cc06050c1a999beb3694.ssl.cf1.rackcdn.com/2b733fc955a2883ef8a7093ff10563f5-32.png",
                        "ui_class": "supporter"
                    }
                }
            }
        ]
    }
