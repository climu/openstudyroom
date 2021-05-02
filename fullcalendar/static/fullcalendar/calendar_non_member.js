function load_calendar(locale, community=null) {

  $('#calendar').fullCalendar({
    locale: locale,
    header: {
      left: 'prev,next today',
      center: 'title',
      right: 'month,agendaWeek'
    },
    views: {
      month: {
        selectable: false,
      }
    },
    weekNumbers: true,
    navLinks: true, // can click day/week names to navigate views
    editable: false,
    height: 'auto',
    allDaySlot: false,
    timeFormat: 'H:mm',
    events: {
      url: '/calendar/json-feed/',
      data: function() { // a function that returns an object
        var div_list = $('.check-div:checkbox:checked').map(function() {
          return this.value;
        }).get();
        json = JSON.stringify(div_list);
        return ({
          'divs': json,
          'community': community,
        });
      }
    },
    eventRender: function(event, element) {
      //public
      if (event.type === 'public') {
        element.qtip({
          content: {
            text: event.description,
            title: event.title,
          },
          position: {
            my: 'left bottom', // Position my top left...
            at: 'right top',
            target: 'mouse', // Use the mouse position as the position origin
            adjust: { // Don't adjust continuously the mouse, just use initial position
              x: 5,
              y: -5
            }
          },
          show: {
            solo: true
          }
        }); //qtip
      } // closing public
    } //event render
  }); //fullCalendar
}
