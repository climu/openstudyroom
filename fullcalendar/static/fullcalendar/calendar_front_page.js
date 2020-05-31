
function load_calendar_member(timezone, locale, start_time_range, end_time_range){
  $('#calendar').fullCalendar({
    locale:locale,
    header: {
        left:'',
        center: 'title',
        right: ''
    },
    weekNumbers: false,
    navLinks: false, // can click day/week names to navigate views
    editable: false,
    allDaySlot:false,
    timeFormat: 'H:mm',
    selectable:false,
    selectHelper: false,
    minTime: start_time_range + ":00:00",
    maxTime: end_time_range + ":00:00",
    height: 'auto',
    views: {
      timeGridFourDay: {
        type: 'agenda',
        duration: { days: 5 },
        visibleRange: function(currentDate) {
          return {
            start: currentDate.clone().subtract(1, 'days'),
            end: currentDate.clone().add(4, 'days') // exclusive end, so 3
          };
        }
      }
    },
    defaultView: 'timeGridFourDay',
    slotDuration :'02:00:00',

    ///////////////////////////////////////////////////////////////
    // Events source
    ///////////////////////////////////////////////////////////
    events:{
        url: '/calendar/json-feed/',
        data: {
                'me-av':true,
                'other-av':true,
                'game-request':true
            }
    },

    ///////////////////////////////////////////////////////////////
    // Event Render
    ///////////////////////////////////////////////////////////
    eventRender: function(event, element) {

        // If envent.type is other-available
        if (event.type === 'other-available'){
            var text ='<ul>';
            event.users.forEach(function(element){
                text +='<li>' + element + '</li>';
            });
            text += '</ul>';
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

        }// other-available

        // My game requests
        if (event.type === 'my-gr'){
            var text = '<ul>';
            event.users.forEach(function(element){
                text +='<li>' + element + '</li>';
            });
            text += '</ul>';
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
            var text = '<p><b>' + event.sender + '</b> want to play with you the ';
            text += event.start.format('lll') + ' (' + timezone + ').<p>'
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


});//fullCalendar
}
