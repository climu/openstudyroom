import datetime
import unittest

import django.test
import pytz

from . import utils
from . import models

class TestSgfModel(django.test.TestCase):
    def test_get_players(self):
        b_u = models.User.objects.create(username='nomenest')
        w_u = models.User.objects.create(username='climu')
        dt = datetime.datetime.min.replace(tzinfo=pytz.utc)
        ev = models.LeagueEvent.objects.create(begin_time=dt, end_time=dt)
        b = models.LeaguePlayer.objects.create(user=b_u, kgs_username='nomeNEST', event=ev)
        w = models.LeaguePlayer.objects.create(user=w_u, kgs_username='climu', event=ev)
        sgf_m = models.Sgf.objects.create(p_status=2, sgf_text=test_sgf)
        sgf_m.parse()
        black, white = sgf_m.get_players(ev)
        assert black == b and white == w

class TestUtils(unittest.TestCase):
    def test_parse_sgf_string(self):
        parsed = utils.parse_sgf_string(test_sgf)
        expected = {
            'date': datetime.datetime(2016, 11, 19, 0, 0),
            'result': 'W+36.50',
            'bplayer': 'nomenest',
            'wplayer': 'climu',
            'komi': 0.50,
            'board_size': 19,
            'time': 60,
            'byo': '1x10 byo-yomi',
            'place': 'The KGS Go Server at http://www.gokgs.com/',
            'number_moves': 268,
            'check_code': '20161119climunomenestmnhnimcf11',
            'handicap': 0,
        }
        assert parsed == expected

test_sgf = '''(;GM[1]FF[4]CA[UTF-8]AP[CGoban:3]ST[2]
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
