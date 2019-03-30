
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

function togglesearch(){
  $('#search_container').toggleClass('hidden')
  if (!($('#search_container').hasClass('hidden'))){
      $('#search-input').focus()
  }
  $('#search-button').toggleClass('text-primary')
}

var autocomplet = debounce(function() {
	var min_length = 2;
	var query = $('#search-input').val();
	if (query.length >= min_length) {
    $('#search-results').show();
    request_users(query)
    request_pages(query)
    request_blog(query)
    request_forum(query)
	} else {
		$('#search-results').hide();
	}
},
250)

function request_forum(query){
  $.ajax({
    url: '/search-api/forum/',
    type: 'GET',
    data: {query:query},
    success:function(data){
      $('#forum-results').empty()
      if (data.length > 0){
        var header = '<a href="/forum/search/?q=' + query + '" class="list-group-item list-group-item-info text-center"> Forum Topics</a>'
        $('#forum-results').html(header)
      }
      for (var i in data){
        page = data[i]
        $('#forum-results').append(format_page_search(page))
      }
    }
  });
  }
function request_pages(query){
  $.ajax({
    url: '/search-api/pages/',
    type: 'GET',
    data: {query:query},
    success:function(data){
      $('#page-results').empty()
      if (data.length > 0){
        $('#page-results').html('<li class="list-group-item list-group-item-info text-center"> Pages</li>')
      }
      for (var i in data){
        page = data[i]
        $('#page-results').append(format_page_search(page))
      }
    }
  });
  }

  function request_blog(query){
    $.ajax({
      url: '/search-api/blog/',
      type: 'GET',
      data: {query:query},
      success:function(data){
        $('#blog-results').empty()
        if (data.length > 0){
          var header = '<a href="/blog/search/?q=' + query + '" class="list-group-item list-group-item-info text-center"> Blog Posts</a>'
          $('#blog-results').html(header)
        }
        for (var i in data){
          page = data[i]
          $('#blog-results').append(format_page_search(page))
        }
      }
    });
    }


function format_page_search(page){
  html = '<a href="' + page.url + '" class="list-group-item" >' + page.title + "</a>"
  return html
}

function request_users(query){
  $.ajax({
    url: '/search-api/users/',
    type: 'GET',
    data: {query:query},
    success:function(data){
      $('#user-results').empty()
      if (data.length > 0){
        $('#user-results').html('<li class="list-group-item list-group-item-info text-center"> Users</li>')
      }
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

// Returns a function, that, as long as it continues to be invoked, will not
// be triggered. The function will be called after it stops being called for
// N milliseconds. If `immediate` is passed, trigger the function on the
// leading edge, instead of the trailing.
function debounce(func, wait, immediate) {
	var timeout;
	return function() {
		var context = this, args = arguments;
		var later = function() {
			timeout = null;
			if (!immediate) func.apply(context, args);
		};
		var callNow = immediate && !timeout;
		clearTimeout(timeout);
		timeout = setTimeout(later, wait);
		if (callNow) func.apply(context, args);
	};
};
