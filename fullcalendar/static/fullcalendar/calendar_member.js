
function load_calendar_member(timezone, locale, start_time_range, end_time_range, community=null){
  $('#calendar').fullCalendar({
    locale:locale,
    customButtons: {
        myCustomButton: {
            text: '?',
            click: function() {
                window.open('/calendar/help/', '_blank');
            }
        }
    },
    header: {
        left: 'prev,next today ',
        center: 'title',
        right: 'month,agendaWeek myCustomButton'
    },
    views: {
        month:{
            selectable:false,
        }
    },
    weekNumbers: true,
    navLinks: true, // can click day/week names to navigate views
    editable: false,
    height: 'auto',
    allDaySlot:false,
    timeFormat: 'H:mm',
    selectable:true,
    selectHelper: true,
    minTime: start_time_range + ":00:00",
    maxTime: end_time_range + ":00:00",

    //prevent user from selecting multiple day availability
    selectConstraint: {
        start: '00:00',
        end: '24:00',
    },

    selectAllow:  function(selectInfo){
        return ($('#me-av-pill').hasClass('active'));
    },
    //we don't want to me-available event overlaping
    selectOverlap: function(event) {
            return event.type != 'me-available';
    },
    eventOverlap: function(stillEvent, movingEvent) {
        return stillEvent.type != 'me-available';
    },

    //selecting will create an event saying user is available
    select: function(start, end) {
        var eventData;
        // the following commented lines is an attempt to set a minimal 1h30
        // The issue is that we then lost overlaping control
        //var duration = end - start ;
        //if (duration < 5400000){
        //  end = start + 5400000 - end;
        //  }
        eventData = {
            title: 'I am available',
            start: start,
            end: end,
            type:'me-available',
            color: '#ffff80',
            className :'me-available',
            is_new : true,
            is_change:true,
            editable:true
        };
        $('#calendar').fullCalendar('renderEvent', eventData, true); // stick? = true
        $('#calendar').fullCalendar('unselect');
        $('#save').attr('class','btn btn-primary');
    },// select

    eventResize: function(event, delta) {
        event.is_change=true;
        $('#save').attr('class','btn btn-primary')
    },

    eventDrop:function(event, delta){
        event.is_change=true;
        $('#save').attr('class','btn btn-primary')
    },

    ///////////////////////////////////////////////////////////////
    // Events source
    ///////////////////////////////////////////////////////////
    events:{
        url: '/calendar/json-feed/',
        data: function() { // a function that returns an object
            var div_list = $('.check-div:checkbox:checked').map(function() {
                return this.value;
            }).get();
            div_list = JSON.stringify(div_list);
            var server_list = $('.check-srv:checkbox:checked').map(function() {
                return this.value;
            }).get();
            server_list = JSON.stringify(server_list);
            return({
                'divs':div_list,
                'servers':server_list,
                'me-av':!($('#cal-pill').hasClass('active')),
                'other-av':($('#other-av-pill').hasClass('active')),
                'game-request':!($('#me-av-pill').hasClass('active')),
                'community': community,
            });
        }
    },

    ///////////////////////////////////////////////////////////////
    // Event Render
    ///////////////////////////////////////////////////////////
    eventRender: function(event, element) {
        if (element.find(".fc-helper")){
            event.eventColor='#ffff80';
        }

        // deals with me-available events:
        if (event.type === 'me-available'){
            // If we are on my availability tab we can change thoses.
            if ($('#me-av-pill').hasClass('active')){
                // add a closeon button
                element.find(".fc-content").prepend( "<span style='font-size:1.5em;'class='pull-right glyphicon glyphicon-remove-circle closeon' aria-hidden='true'></span>" );
                element.find(".closeon").click(function() {
                    //if the event is not new, we have to create a deleted event to inform the server
                    if (event.is_new != true){
                        event.type = 'deleted';
                        event.is_change = true;
                        event.className  = 'event-deleted';
                        event.rendering  = 'background';
                        $('#calendar').fullCalendar('updateEvent', event);
                        $('#save').attr('class','btn btn-primary')
                    }
                    else{
                        $('#calendar').fullCalendar('removeEvents',event._id);
                    }
                });// end of closeon
            }
            else if ($('#other-av-pill').hasClass('active')) {
                element.find(".fc-content").hide();
                if (!($('#check-own')[0].checked)) {
                    element.addClass('hidden');
                }
            }
            else{
                element.addClass('hidden');
            }
        }// end of event.type == me-available

        // If envent.type is other-available
        if (event.type === 'other-available'){
            element.addClass('click-me');
            element.append(event.title);
            var text ='<ul>';
            event.users.forEach(function(element){
                text +='<li>' + element + '</li>';
            });
            text += '</ul> <p> Click to create a game request.</p>';
            element.qtip({
                content:{
                    title:event.title,
                    text: text,
                },
                position: {
                    my:'left bottom',  // Position my top left...
                    at:'right top',
                    target: 'mouse', // Use the mouse position as the position origin
                    adjust: { // Don't adjust continuously the mouse, just use initial position
                        x:5,
                        y:-5
                    }
                },
                show: {solo: true}
            });//tooltip

            element.attr('data-users', event.users);
            if (!($('#other-av-pill').hasClass('active'))){
                element.addClass('hidden');
            }
        }// other-available

        // My game requests
        if (event.type === 'my-gr'){
            element.addClass('click-me');
            var text = '<ul>';
            event.users.forEach(function(element){
                text +='<li>' + element + '</li>';
            });
            text += '</ul> <p> Click to cancel game request.</p>';
            element.qtip({
                content: {
                    text: text,
                    title: 'Waiting on confirmation from:'
                },
                position: {
                    my:'left bottom',  // Position my top left...
                    at:'right top',
                    target: 'mouse', // Use the mouse position as the position origin
                    adjust: { // Don't adjust continuously the mouse, just use initial position
                        x:5,
                        y:-5
                    }
                },
                show: {solo: true}
            });//tooltip
        }// my game requests

        //other-gr
        if (event.type === 'other-gr'){
            element.addClass('click-me');
            var text = '<p><b>' + event.sender + '</b> want to play with you the ';
            text += event.start.format('lll') + ' (' + timezone + ').<p>'
            text += '<p>Click to accept or reject game request</p>'
            element.qtip({
                content: {
                    text: text,
                    title: 'Game request from ' + event.sender,
                },
                position: {
                    my:'left bottom',  // Position my top left...
                    at:'right top',
                    target: 'mouse', // Use the mouse position as the position origin
                    adjust: { // Don't adjust continuously the mouse, just use initial position
                        x:5,
                        y:-5
                    }
                },
                show: {solo: true}
            });//tooltip
        }//other gr

        //game appointments
        if (event.type === 'game'){
            element.addClass('click-me');
            element.qtip({
                content: {
                    text: 'Click to cancel this game appointment.',
                    title: event.title,
                },
                position: {
                    my:'left bottom',  // Position my top left...
                    at:'right top',
                    target: 'mouse', // Use the mouse position as the position origin
                    adjust: { // Don't adjust continuously the mouse, just use initial position
                        x:5,
                        y:-5
                    }
                },
                show: {solo: true}
            });//qtip
        }//game appointments

        //public events
        if (event.type === 'public'){
            element.qtip({
                content: {
                    text: event.description,
                    title: event.title,
                },
                position: {
                    my:'left bottom',  // Position my top left...
                    at:'right top',
                    target: 'mouse', // Use the mouse position as the position origin
                    adjust: { // Don't adjust continuously the mouse, just use initial position
                        x:5,
                        y:-5
                    }
                },
                show: {solo: true}
            });//qtip
        }// closing public
    }, // Closing render event

    ///////////////////////////////////////////////////////////////
    // Event click and day click for background events
    ///////////////////////////////////////////////////////////
    eventClick: function(calEvent, jsEvent, view) {
        // My game requests
        if (calEvent.type == 'my-gr'){
            $("#modal-message").hide();
            $(".modal-button").hide();
            calEvent.className = 'my-gr-active';
            $("#modal-title").text('Game request on ' + calEvent.start.format('lll') + ' (' + timezone + ')');
            $("#modal-body").empty();
            $("#modal-body").append('<p>Waiting on this users confirmation:</p>');
            $("#modal-body").attr('data-pk', calEvent.pk);
            $("#modal-body").append('<p><ul>');
            calEvent.users.forEach(function(user){
                $("#modal-body").append('<li>' + user + '</li>')
            });
            $("#modal-body").append('</ul></p>');
            $("#cancel-game-request").show();
            $("#game-request-modal").modal();
            $("#game-request-modal").draggable({handle : ".modal-header"});
        }//My game requests

        // Others game requests
        if (calEvent.type == 'other-gr'){
            $("#modal-message").hide();
            $(".modal-button").hide();
            $("#modal-title").text(calEvent.sender + ' game request on ' + calEvent.start.format('lll') + ' ('+ timezone + ')');
            $("#modal-body").empty();
            $("#modal-body").append('<p><u>'+ calEvent.sender +'</u> want to play with you.</p>');
            $("#modal-body").attr('data-pk', calEvent.pk);
            $("#accept-game-request").show();
            $("#reject-game-request").show();
            $("#game-request-modal").modal();
            $("#game-request-modal").draggable({handle : ".modal-header"});
        }// Other game requests

        // Game
        if (calEvent.type == 'game'){
            $("#modal-message").hide();
            $(".modal-button").hide();
            $("#modal-title").text(calEvent.title + ' on ' + calEvent.start.format('lll') + ' (' + timezone + ')');
            $("#modal-body").empty();
            $("#modal-body").append('<p>Are you sure you want to cancel this game appointment?</p>');
            $("#modal-body").attr('data-pk', calEvent.pk);
            $("#cancel-game").show();
            $("#game-request-modal").modal();
            $("#game-request-modal").draggable({handle : ".modal-header" });
        }//Game
    },// event click

    // Day click
    dayClick: function(date, jsEvent, view) {
        var element = jsEvent.target;
        // check if we clicked on a other-available event
        if (element.classList.contains('other-available')) {
            // empty the message
            $("#modal-message").hide();
            $(".modal-button").hide();
            // get the users available at that time in an array
            var users = element.getAttribute('data-users').split(',').sort();
            $("#modal-title").text('Request a game on ' + date.format('lll') + ' (' + timezone + ')');
            $("#modal-body").empty();
            $("#modal-body").append('<p>Select the users you want to send a game request to:</p>');
            $("#modal-body").attr('data-date', date.format());
            users.forEach(function(element){
                $("#modal-body").append(
                    '<div class="checkbox"><label><input class="user-select" type="checkbox" value="'+
                    element + '" checked>'+ element + '</label></div>');
            });

            $("#send-game-request").show();
            $("#game-request-modal").modal();
            $("#game-request-modal").draggable({handle : ".modal-header"});
        }// we clicked on other-available event
    },//dayclick


});//fullCalendar

///////////////////////////////////////////////////////////////
// Buttons handling
///////////////////////////////////////////////////////////

// Cancel game appointment
$('#cancel-game').click(function(){
    var pk = $('#modal-body').attr('data-pk');
    $.ajax({
        type:"POST",
        url:"/calendar/cancel-game-ajax/",
        data: {'pk': pk},
        error:function(){
          alert("Something went wrong. For some reason we couldn't cancel this game request. Please try again and if the issue remain, report to climu this code: cm4")
        }
    });
    $('#game-request-modal').modal('hide');
    $('#calendar').fullCalendar( 'removeEvents');
    $('#calendar').fullCalendar( 'refetchEvents' );
    return false;
});//Cancel Game

// handle the accept game request click
$('#accept-game-request').click(function(){
    var pk = $('#modal-body').attr('data-pk');
    $.ajax({
        type:"POST",
        url:"/calendar/accept-game-request-ajax/",
        data: {'pk': pk},
        error:function(){
          alert("Something went wrong. For some reason we couldn't accept this game request. Please try again and if the issue remain, report to climu this code: cm5")
        }
   });
   $('#game-request-modal').modal('hide');
   $('#calendar').fullCalendar( 'removeEvents');
   $('#calendar').fullCalendar( 'refetchEvents' );
   return false;
});//accept Game request

// handle the reject game request click
$('#reject-game-request').click(function(){
    var pk = $('#modal-body').attr('data-pk');
    $.ajax({
        type:"POST",
        url:"/calendar/reject-game-request-ajax/",
        data: {'pk': pk},
        error:function(){
          alert("Something went wrong. For some reason we couldn't accept this game request. Please try again and if the issue remain, report to climu this code: cm6")
        }
    });
    $('#game-request-modal').modal('hide');
    $('#calendar').fullCalendar( 'removeEvents');
    $('#calendar').fullCalendar( 'refetchEvents' );
    return false;
});//reject Game request

// handle the cancel game request click
$('#cancel-game-request').click(function(){
    var pk = $('#modal-body').attr('data-pk');
    $.ajax({
        type:"POST",
        url:"/calendar/cancel-game-request-ajax/",
        data: {'pk': pk},
        error:function(){
          alert("something went wrong. Please report to climu this code: cm6")
        }
    });
    $('#game-request-modal').modal('hide');
    $('#calendar').fullCalendar( 'removeEvents');
    $('#calendar').fullCalendar( 'refetchEvents' );
    return false;
});//cancel-game-request

// handle the send game request click
$('#send-game-request').click(function(){
    // get the list of selected users
    var selected_users = $('.user-select:checked').map(function(){
        return this.value;
    }).get();
    // This list shouldn't be empty
    if (selected_users.length == 0 ) {
        $('#modal-message').text('You should select at least one user.');
        $('#modal-message').addClass("alert alert-warning");
        $('#modal-message').show()
        return;
    }
    var date = $('#modal-body').attr('data-date');
    json = JSON.stringify(selected_users);
    $.ajax({
        type:"POST",
        url:"/calendar/create-game-request/",
        data: {
            'date': date,
            'users': json
        },
        error:function(){
          alert("something went wrong. Please report to climu this code: cm0")
        }
    });
    $('#game-request-modal').modal('hide');
    $('#calendar').fullCalendar( 'removeEvents');
    $('#calendar').fullCalendar( 'refetchEvents' );
    return false;
});// Closing the send game request click

// Save button
$("#save").click(function () {
    var eventsFromCalendar = $('#calendar').fullCalendar('clientEvents',function (event) {
        return event.is_change == true;});
    //to render json from events objects list, we need to deal with circular relation
    //see https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Errors/Cyclic_object_value
    eventsFromCalendar = eventsFromCalendar.map(function(e) {
        return {
            start: e.start,
            end: e.end,
            title: e.title,
            type: e.type,
            is_new: e.is_new,
            id:e.id,
            pk:e.pk
        };
    });
    seen = [];
    var json = JSON.stringify(eventsFromCalendar,function(key, val) {
        if (val != null && typeof val == "object") {
            if (seen.indexOf(val) >= 0) {
                return;
            }
            seen.push(val);
        }
        return val;
    });// end of circular relation thing I don't understand

    $.ajax({
        type:"POST",
        url:"/calendar/save/",
        data: {
           'events': json
        },
        error:function(){
          alert("something went wrong. Please report to climu this code: cm1")
        }
   });
   $('#calendar').fullCalendar( 'removeEvents');
   $('#calendar').fullCalendar( 'refetchEvents' );
   $('#save').attr('class','btn btn-default')
   return false;
});// closing $("#save").click


// when a user (un)check a division checkbox
// we need to refetch the events
$('.refetch').click(function(){
    //$('#calendar').fullCalendar( 'removeEvents');
    $('#calendar').fullCalendar( 'refetchEvents' );
});

// Toggle showing his own availibility
$('#check-own').click(function(){
    if ($('#check-own')[0].checked){
        $('.me-available').removeClass('hidden')
    }
    else{
        $('.me-available').addClass('hidden')
    }
});

//copy previous week
$("#copy").click(function () {
    var start = $('#calendar').fullCalendar('getView').start;
    var end = $('#calendar').fullCalendar('getView').end;

    //check if the week is empty
    var eventsFromCalendar = $('#calendar').fullCalendar('clientEvents', function (event) {
        return ( event.type == 'me-available' && event.start > start && event.end < end)});
    if (eventsFromCalendar.length >0) {
        alert('You canot copy previous week because this week is not empty')
        return false
    }
    var start = $('#calendar').fullCalendar('getView').start;
    $.ajax({
        type:"POST",
        url:"/calendar/copy-previous-week-ajax/",
        data: {
            'start': start.format(),
            'end': end.format()
        },
        error:function(){
          alert("something went wrong. Please report to climu this code: cm2")
        }
    });
$('#calendar').fullCalendar( 'refetchEvents' );
});

///////////////////////////////////////////////////////////////
// Filter time range
///////////////////////////////////////////////////////////

$('#filter-time-range').click(function(){
    var range = $('#slider').bootstrapSlider('getValue');
    var start = range[0].toString() + ":00:00" ;
    var end = range[1].toString() + ":00:00" ;
    $('#calendar').fullCalendar('option', 'minTime', start);
    $('#calendar').fullCalendar('option', 'maxTime', end);
    $.ajax({
        type:"POST",
        url:"/calendar/update-time-range-ajax/",
        data: {
            'start': range[0],
            'end': range[1]
        },
        error:function(){
          alert("something went wrong. Please report to climu this code: cm3")
        }
    });
});

// When the slider change value, we...
$('#slider').bootstrapSlider().on('change',function(slider){
    var start = slider.value.newValue[0].toString() + ":00" ;
    var end = slider.value.newValue[1].toString() + ":00" ;
    $('#start-time-range').html(start);
    $('#end-time-range').html(end);
});

///////////////////////////////////////////////////////////////
// Menu handling
///////////////////////////////////////////////////////////

$('#me-av-pill').click(function() {
    $('#save').attr('class','btn btn-default');
    $('li[role="presentation"]').removeClass('active');
    $(this).addClass('active');
    $(".other-available-controls").addClass('hidden');
    $(".me-available-controls").removeClass('hidden');
    $("#info-well").text('Drag vertically on the calendar to indicate when you are available.')
    $('#calendar').fullCalendar( 'removeEvents');
    $('#calendar').fullCalendar('changeView', 'agendaWeek');
    $('#calendar').fullCalendar( 'refetchEvents' );
});

$('#other-av-pill').click(function() {
    $('li[role="presentation"]').removeClass('active');
    $(this).addClass('active');
    $(".me-available-controls").addClass('hidden');
    $(".other-available-controls").removeClass('hidden');
    $("#info-well").text('See when other users are available and manage game requests.')
    $('#calendar').fullCalendar( 'removeEvents');
    $('#calendar').fullCalendar('changeView', 'agendaWeek');
    $('#calendar').fullCalendar( 'refetchEvents' );
});

$('#cal-pill').click(function() {
    $('li[role="presentation"]').removeClass('active');
    $(this).addClass('active');
    $(".me-available-controls").addClass('hidden');
    $(".other-available-controls").addClass('hidden');
    $("#info-well").text('Browse all your OSR events.')
    $('#calendar').fullCalendar( 'removeEvents');
    $('#calendar').fullCalendar('changeView', 'month');
    $('#calendar').fullCalendar( 'refetchEvents' );
});

}
