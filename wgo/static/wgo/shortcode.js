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
function tags_to_JSON(tag){
    tag = tag.replace('goban','')
    tag = tag.replace(']',' ]')
    equal = tag.indexOf('=')
    start = 1
    var dict = {}
    while ((equal != -1)){
        key = tag.substr(start,equal-start).replace(' ','')
        start = tag.indexOf(' ', equal) + 1
        value = tag.substr(equal+1, start - equal-2).replace(' ','')
        dict[key]=value
        equal = tag.indexOf('=', start)
    }
    console.log(dict)
    return dict
}

/*
converts JSON and coments to html string
*/
function JSON_to_html(json,comments){

    tag_open = '<div '
    tag_content = ''
    tag_close = '></div>'

    //set source sgf file
    if (json['sgf']){
        tag_content += ' data-wgo=" ' + json['sgf'] + ' " '
    }else{// this should be refine. Doesn't work in preview
        tag_content += ' data-wgo=" ' + $("div.attachment").find('a').attr('href') + ' " '
    }

    // activate coordinates or diagram
    if (json['diagram'] ){
        // set empty layout disable scroll and keys
        tag_content += ' data-wgo-layout="" data-wgo-enablewheel="false" data-wgo-enablekeys="false"';
        // set limits of the diagram
        if (json['limits']){
            args = json['limits'].split(',')
            config=" section:{top:'" + args[0] +  "', right:'" + args[1] +  "', bottom:'" + args[2] +  "', left:'" + args[3] +  "'}"
            tag_content += 'data-wgo-board=" ' + config +'"';
         // if no limits, we can show coordinates unless coord !=='true'
        }else if (json['coord']){
            var js = "arguments[0].target.setCoordinates(true);";
            tag_content += 'data-wgo-onkifuload="' + js + '"';

         }
    }else{// if no diagram, we activate coordinate by default and allow layout=simple
        //coordinates
        if (json['coord']){
            var js = "arguments[0].target.setCoordinates(true);";
            tag_content += 'data-wgo-onkifuload="' + js + '"';
        }// coordiantes are deactivated by default, so no need to do anything if coord != true
        else{// activate coordinates by default
            var js = "arguments[0].target.setCoordinates(true);";
            tag_content += 'data-wgo-onkifuload="' + js + '"';
        }
         //set minimal layout
         if (json['simple']){
             var layout = "bottom: ['Control']";
             tag_content += ' data-wgo-layout="' + layout + '" ';
         }
     }

    //set goban to specific move
    if (json['move']){
        tag_content += ' data-wgo-move= " ' + json['move'] + ' " '
    }else{
        tag_content += ''
    }

     // set style
     tag_content += ' style="'
     //width
     if (json['width']){
         tag_content += 'width:' + json['width'] + '; '
     }
     if (json['float']){
         tag_content += 'float:' + json['float'] + '; '
     }
     tag_content += '"'


// get the count of player on the page
n = $('#count-wgo').attr('data-count-wgo') ;


    //parse the content to add info to the coords and moves
    //coords
    str = comments
    matches = str.match(/[A-T][0-9]{1,2}/igm);
    if (matches !== null){
        for(i = 0 ; i < matches.length; i++){
            repl = '<a href="javascript:void(0)"  class="coord" data-target="wgo_' + n + '">' + matches[i] + '</a>'
            str = str.replace(matches[i],repl)
        }
    }
    //moves
    matches = str.match(/move [0-9]{1,3}/igm);
    if (matches !== null){
        for(i = 0 ; i < matches.length; i++){
         repl = '<a href="javascript:void(0)"  class="move" data-target="wgo_' + n + '">' + matches[i] + '</a>'

        str = str.replace(matches[i],repl)
         }
     }
     tag_close += str;


 // increment the wgo count

 $('#count-wgo').attr('data-count-wgo', parseInt(n) +1);

return tag_open + tag_content + tag_close ;

}
/*
replaces the first [goban][/goban] in str by a html goban
*/
function goban_html_single(str){
    //check if there is a goban tag
    regex_main = /\[ *?goban.*?\](.|\n)*?\[ *?\/ *?goban *?\]/
    if(!regex_main.test(str))
        return false

    //find relevant text
    goban = str.match(regex_main)[0]

    tag = goban.match(/\[ *?goban.*?\]/)[0]
    endtag = goban.match(/\[ *?\/ *?goban *?\]/)[0]
    comments = goban.substring(tag.length,goban.length-endtag.length)

    /*
    goban_final = function_that_makes_goban_html(tags_to_JSON(tag),comments)
    */
    goban_final = JSON_to_html(tags_to_JSON(tag),comments) //temp

    return str.replace(regex_main,goban_final)
}

/*
replaces every [goban][/goban] in str by a html goban
*/
function preprocessor(str){
    while(x = goban_html_single(str)){str = x}
    return str
}
