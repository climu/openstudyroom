
/*
replaces the first [gmt][/gmt] in str by a formated datetime
*/
function gmt_html_single(str, tz, offset){
    //check if there is a gmt tag
    regex_main = /\[ *?gmt.*?\](.|\n)*?\[ *?\/ *?gmt *?\]/
    if(!regex_main.test(str))
        return false

    //find relevant text
    gmt = str.match(regex_main)[0]

    tag = gmt.match(/\[ *?gmt.*?\]/)[0]
    endtag = gmt.match(/\[ *?\/ *?gmt *?\]/)[0]
    time_string = gmt.substring(tag.length,gmt.length-endtag.length)
    date_utc = moment.utc(time_string,'YYYY-MM-DD HH:mm')
    date_tz = date_utc.add(offset, 's')
    html = date_tz.format('LLLL') + ' (' + tz + ')'


    return str.replace(regex_main,html)
}

/*
replaces every [gmt][/gmt] in str by a html gmt
*/
function gmt_preprocessor(str, tz, offset){
    while(x = gmt_html_single(str, tz, offset)){str = x}
    return str
}

function gmt(selector, tz, offset){
  selector.each(function() {
    str = gmt_preprocessor($( this ).html(), tz, offset)
    $( this ).html(str)
})
}
