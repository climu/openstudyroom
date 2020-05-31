from django import template

register = template.Library()


@register.filter
def prepare_sgf(sgf):
    sgf = sgf.replace(';B[]', "").replace(';W[]', "").replace(';)', '').replace(':/', "").replace(';-)', '')
    return sgf

@register.filter
def prepare_sgf_file(value):
    f = value.file
    f.open(mode='rb')
    sgf = f.read()
    sgf = str(sgf, 'utf-8')
    sgf = sgf.replace(chr(34), "")
    return sgf
#    return "(;PB[Black]PW[White]RE[B+R];B[qd];W[dd];B[pq];W[dq];B[fc])"
