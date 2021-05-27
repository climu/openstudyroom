const prefix = '/calendar/';

class PublicEventSource {
  constructor() {
    this.id = 'public';
    this.url = prefix + 'get-public-events';
  }
  eventDataTransform(e) {
    e.className = 'public-event';
  }
}

class UserAvailableEventSource {
  constructor() {
    this.id = 'user-available';
    this.url = prefix + 'get-user-available-events';
  }
  eventDataTransform(e) {
    e.editable = true;
    e.title = `I'm available`;
    e.className = e.type;
    e.display = $('#user-av-event-filter').is(':checked') ? 'block' : 'none';
  }
}

class OpponentAvailableEventSource {
  constructor() {
    this.id = 'opponent-available';
    this.url = prefix + 'get-opponent-available-events';
    this.extraParams = () => ({
      divisions: JSON.stringify(getDivisionList())
    });
  }
  eventDataTransform(e) {
    e.title = e.opponents.join(', ');
    e.className = 'opponent-available-event';
    e.display = $('#opponents-av-event-filter').is(':checked') ? 'block' : 'none';
  }
}

class RequestEventSource {
  constructor() {
    this.id = 'request';
    this.url = prefix + 'get-game-request-events';
    this.extraParams = () => ({
      divisions: JSON.stringify(getDivisionList())
    });
  }
  eventDataTransform(e) {
    console.log(e.type)
    if (e.type === 'user-game-request') {
      e.title = `Me vs ${e.receivers.join(', ')}`;
    } else {
      e.title = `Me vs ${e.sender}`;
    }
    e.className = e.type;
    e.display = $('#request-event-filter').is(':checked') ? 'block' : 'none';
  }
}

class AppointmentsEventSource {
  constructor() {
    this.id = 'appointment';
    this.url = prefix + 'get-game-appointment-events';
    this.extraParams = () => ({
      divisions: JSON.stringify(getDivisionList()),
      only_user: $('#only-user-filter').is(':checked')
    });
  }
  eventDataTransform(e) {
    if (e.type === 'user-game-appointment') {
      e.title = `Me vs ${e.opponent}`;
      e.display = $('#appointment-event-filter').is(':checked') ? 'block' : 'none';
    } else {
      e.title = `${e.users[0]} vs ${e.users[1]}`;
      e.display = $('#appointment-event-filter').is(':checked') && !$('#only-user-filter').is(':checked') ? 'block' : 'none';
    }
    e.className = e.type;

  }
}

class Calendar extends FullCalendar.Calendar {
  constructor(id) {
    const container = document.getElementById(id);
    super(container, {
      height: 'auto',
      expandRows: false,
      allDaySlot: false,
      eventDisplay: 'block',
      initialView: 'timeGridWeek',
      headerToolbar: {
        left: 'prev,next today',
        center: 'title',
        right: 'dayGridMonth,timeGridWeek'
      },
      selectable: true,
      selectMirror: true,
      timeZone: 'UTC',

    });
    this.render();
  }
}

function getDivisionList() {
  const elements = Array.from(document.getElementsByClassName('league-event-filter'));
  return elements.filter(e => e.checked).map(e => e.value);
}

const calendar = new Calendar('calendar');
calendar.addEventSource(new PublicEventSource());
calendar.addEventSource(new OpponentAvailableEventSource());
calendar.addEventSource(new RequestEventSource());
calendar.addEventSource(new UserAvailableEventSource());
calendar.addEventSource(new AppointmentsEventSource());

$('.league-event-filter').change((e) => {
  calendar.getEventSourceById('opponent-available').refetch();
  calendar.getEventSourceById('request').refetch();
});

$('#user-av-event-filter').change((e) => {
  calendar.getEvents().filter(e =>
    e.extendedProps.type === 'user-available').forEach(e => {
    e.setProp('display',
      $('#user-av-event-filter').is(':checked') ? 'block' : 'none');
  });
});

$('#opponents-av-event-filter').change((e) => {
  calendar.getEvents().filter(e =>
    e.extendedProps.type === 'opponents-available').forEach(e => {
    e.setProp('display',
      $('#opponents-av-event-filter').is(':checked') ? 'block' : 'none');
  });
});

$('#request-event-filter').change((e) => {
  calendar.getEvents().filter(e =>
    e.extendedProps.type === 'user-game-request' ||
    e.extendedProps.type === 'opponent-game-request').forEach(e => {
    e.setProp('display',
      $('#request-event-filter').is(':checked') ? 'block' : 'none');
  });
});

$('#appointment-event-filter').change((e) => {
  calendar.getEvents().filter(e =>
    e.extendedProps.type === 'user-game-appointment').forEach(e => {
    e.setProp('display',
      $('#appointment-event-filter').is(':checked') ? 'block' : 'none');
  });
  calendar.getEvents().filter(e =>
    e.extendedProps.type === 'others-game-appointment').forEach(e => {
    e.setProp('display',
      $('#appointment-event-filter').is(':checked') &&
      !$('#only-user-filter').is(':checked') ? 'block' : 'none');
  });
});

$('#only-user-filter').change((e) => {
  calendar.getEvents().filter(e =>
    e.extendedProps.type === 'others-game-appointment').forEach(e => {
    e.setProp('display',
      $('#only-user-filter').is(':checked') ? 'none' : 'block');
  });
});
