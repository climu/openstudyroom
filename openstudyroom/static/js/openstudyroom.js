
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

/*
Autocomplete search field with ajax requests
*/


function autocomplet() {
	var min_length = 2;
	var query = $('#search-input').val();
  $('#user-results').html('<li class="list-group-item list-group-item-info text-center"> Users</li>')
	if (query.length >= min_length) {
    request_users(query)
	} else {
		$('#search-results').hide();
	}
}

function request_users(query){
  $.ajax({
    url: '/search-api/users/',
    type: 'GET',
    data: {query:query},
    success:function(data){
      for (var i in data){
        user = data[i]
        $('#user-results').append(format_user_search(user))
      }

      $("[data-toggle=tooltip]").tooltip();
    }
  });
}

function format_user_search(user){
    var tooltip = ""
    var online = false
    if ("kgs_username" in user){
      tooltip += '<p'
      if (user["kgs_online"]){
        online = true
        tooltip += " class='online'"
      }else{
        tooltip += " class='offline'"
      }
      tooltip += '>KGS: ' + user["kgs_username"] + ' ' +  user["kgs_rank"] + '</p>'
    }
    if ("ogs_username" in user) {
      tooltip += '<p'
      if (user["ogs_online"]){
        online = true
        tooltip += " class='online'"
      }else{
        tooltip += " class='offline'"
      }
      tooltip += '>OGS: ' + user["ogs_username"] + ' ' +  user["ogs_rank"] + '</p>'
    }
    if ("discord_user" in user) {
      if (discord_user.status == "offline"){
        online = true
      }
      tooltip += "<p class='" + discord_user.status + "'>Discord: "
      tooltip += discord_user.username + ' (' + discord_user.discriminator + ')</p>'
    }
      var html = '<a href="/league/account/' + user['username'] + '/" class="list-group-item'
    if (online){
          html += ' online"'
    }else{
          html += ' offline"'
    }
    html += 'data-toggle="tooltip" data-html="true" rel="tooltip" title="' + tooltip
    html += '">' + user['username'] +'</a>'
    return(html)
  }
