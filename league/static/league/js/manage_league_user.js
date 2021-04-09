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
    content += '<form><div class="form-row form-group"><div class="col-md-6">'
    content += '<label>' + league.name + '</label></div></div>'

    // select division
    content += '<div class="col-md-6"><select data-league="' + league.pk + '"class="form-control"' +  disabled + '>'
    content += '<option value="0"></option>'
    league.divisions.forEach((division, i) => {
      content += '<option value="' + division.pk + '"'
      if (division.is_in){
        content += ' selected '
      }
      content += '>' + division.name + '</option>'
    });
    content += '</select></div></div></form>'
  });
  $('#userLeagueModalBody').html(content)
  $('#userLeagueModal').modal()
  $('#userLeagueModalSave').off('click').on('click',function() {postUserLeague(data.user_pk)})

}

var postUserLeague = function(userId){
  leaguesList = []
  $('#userLeagueModalBody').find("select").each(function( index ) {
    leaguesList.push({
      'leagueId': $( this ).data('league'),
      'divisionId': $( this ).find('option:selected')[0].value
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
