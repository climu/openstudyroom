var get_modal_datas = function(userId, communityId=null){
    $.ajax({
      url: '/league/user-leagues-manage/' + userId + '/',
      type: 'GET',
      data: {community:communityId},
      success:function(data){
        renderModal(data)
      }
    });
}

var renderModal = function(data){
  // add user attr to save button
  $('#userLeagueModalTitle').text(data.username + ' leagues')
  content = ''
  data.leagues.forEach((league, i) => {
    // disable?
    var disabled =''
    if ((league.is_in && !(league.can_quit)) || (!(league.is_in) && !(league.can_join))){
      disabled = 'disabled'
    }
    content += '<div class="checkbox' + disabled + '"> <label><input type="checkbox" value="'
    content += league.pk + '"' + disabled
    if (league.is_in) {
      content += " checked "
    }
    content += '>' + league.name + '</label></div>'

  });
  $('#userLeagueModalBody').html(content)
  $('#userLeagueModal').modal()
  $('#userLeagueModalSave').off('click').on('click',function() {postUserLeague(data.user_pk)})

}

var postUserLeague = function(userId){
  leaguesList = []
  $('#userLeagueModalBody').find("input[type='checkbox']").each(function( index ) {
    leaguesList.push({
      'leagueId': $( this )[0].value,
      'is_in': $( this )[0].checked
    })
  });
  $.ajax({
    url: '/league/user-leagues-manage/' + userId + '/',
    type: 'POST',
    data: {"leaguesList": JSON.stringify(leaguesList)},
    success:function(answer){
      $('#userLeagueModal').modal('hide')
    }
  });

}
