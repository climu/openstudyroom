/*
converts the settings in the goban tag to JSON
We have 2 indexes: start and equal.
Start starts at 0.
We look for the first '=' after start that index equal. then we:
- get key by looking for the space between start and equal.
- get value by looking for first space after equal. New index : start

we loop until no equal is to be found after start.
ugly isn't it?
*/

function glift_html(comments){

    tag_open = '<div class="glift-div" style="height: 400px;width: 100%;" data-sgf=' + comments
    tag_close = '></div>'


return tag_open + tag_close ;

}
/*
replaces the first [goban][/goban] in str by a html goban
*/
function glift_html_single(str){
    //check if there is a goban tag
    regex_main = /\[ *?glift.*?\](.|\n)*?\[ *?\/ *?glift *?\]/
    if(!regex_main.test(str))
        return false

    //find relevant text
    goban = str.match(regex_main)[0]

    tag = goban.match(/\[ *?glift.*?\]/)[0]
    endtag = goban.match(/\[ *?\/ *?glift *?\]/)[0]
    comments = goban.substring(tag.length,goban.length-endtag.length)

    /*
    goban_final = function_that_makes_goban_html(tags_to_JSON(tag),comments)
    */
    goban_final = glift_html(comments) //temp

    return str.replace(regex_main,goban_final)
}

/*
replaces every [goban][/goban] in str by a html goban
*/
function glift_preprocessor(str){
    while(x = glift_html_single(str)){str = x}
    return str
}
