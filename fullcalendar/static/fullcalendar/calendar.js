/**
 * Converts hexadecimal color in rgba format.
 * Used by public events.
 * @param {string|number} hex - the color to convert
 * @returns {string} - the converted color
 */
 function hexToRgba(hex, a=1) {
  var result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return !result ? null : {
    r: parseInt(result[1], 16),
    g: parseInt(result[2], 16),
    b: parseInt(result[3], 16),
    a
  };
}

/**
 * Just a basic wrapper with handy searching methods.
 * @param {object} data - raw data sent by the server
 */
class User {
  constructor(data) {
    Object.assign(this, data);
  }

  /**
   * Checks if the user is in given league.
   * @param {number} pk - the primary key of the league
   * @returns {boolean}
   */
  isLeagueMember = (pk) =>
    !!this.divisions.find(({league}) => league.pk === parseInt(pk));

  /**
   * Checks if the user is in given community.
   * @param {number} pk - the primary key of the community
   * @returns {boolean}
   */
  isCommunityMember = (pk) =>
    !!this.communities.find(community => community.pk === parseInt(pk));

  /**
   * Filter user's divisions that also have a given opponent.
   * @param {number} opponentPk - the primary key of the opponent
   * @returns {array} - the filtered divisions
   */
  getDivisionIntersection = (opponentPk) =>
    this.divisions.filter(({users}) => users.map(({ pk }) => pk).includes(parseInt(opponentPk)));
}

/**
 * Stores data sent by the server.
 * If the user is anonym, Context.user is null. We use that condition
 * accross the app to determine witch services a user have access to.
 */
class Context {
  static rawData =  JSON.parse(document.getElementById('context-data').textContent);
  static communities = Context.rawData.communities || null;
  static leagues = Context.rawData.leagues || null;
  static profil = Context.rawData.profil || null;
  static community = Context.rawData.community || null;
  static user = Context.rawData.user ? new User(Context.rawData.user) : null;
}

/**
 * Manages filtering state of the calendar by
 * listenning input's change.
 */
class Filter {
  static values = (els) => els.filter(el => !el.disabled && el.checked).map(el => parseInt(el.value));

  static el = {
    onlyUser: document.getElementById('only-user-filter'),
		osr: document.getElementById('osr-filter'),
		communities: Array.from(document.getElementsByClassName('community-filter')),
		leagues: Array.from(document.getElementsByClassName('league-filter')),
		public: document.getElementById('public-filter'),
		appointment: document.getElementById('appointment-filter'),
		gameRequest: document.getElementById('game-request-filter'),
		available: document.getElementById('av-event-filter'),
		userAvailable: document.getElementById('user-av-event-filter')
  }

  static get communities() {
    return Filter.values(Filter.el.communities);
  }

  static get leagues() {
    return Filter.values(Filter.el.leagues);
  }

  static get check() {
    return {
      osr: Filter.el.osr && Filter.el.osr.checked,
      public: Filter.el.public && Filter.el.public.checked,
      appointment: Filter.el.appointment && Filter.el.appointment.checked,
      request: Filter.el.gameRequest && Filter.el.gameRequest.checked,
      available: Filter.el.available && Filter.el.available.checked,
      userAvailable: Filter.el.userAvailable && Filter.el.userAvailable.checked,
    }
  }

  static get canEditAvailability() {
    return Filter.check.available && Filter.check.userAvailable;
  }

  static initialize() {
    // Init tooltips
    tippy('#only-info', {content: "Uncheck all community and league filter of which you are not part of"});
    tippy('#community-info', {content: "Filter all events by community"});
    tippy('#league-info', {content: "Filter game requests and appointements by league"});
    tippy('#event-info', {content: "Filter events by their type"});
    tippy('#available-info', {content: "When selected, dragging vertically on the calendar now update your availabilities."});

    Filter.el.appointment.onchange = Calendar.update;
    Filter.el.osr.onchange = Calendar.update;
    Filter.el.public.onchange = Calendar.update;

    Filter.el.communities.forEach(el => el.onchange = (e) => {
      const pk = parseInt(e.target.value);
      const leaguesPk = Context.leagues.filter(league =>
        !!league.community && league.community.pk === pk).map(league => league.pk)
      Filter.el.leagues.forEach(el => {
        if (leaguesPk.includes(parseInt(el.value))) {
          el.disabled = !e.target.checked;
        }
      })
      Calendar.update();
    });

    Filter.el.leagues.forEach(el => el.onchange = () => {
      if (Context.user) { Calendar.refetch(OpponentsAvailableSource); }
      Calendar.update();
    });

    if (Context.user) {
      Filter.el.gameRequest.onchange = Calendar.update;

      Filter.el.onlyUser.onchange = () => {
        const inputs = [
          ...Filter.el.communities.filter(com => !Context.user.isCommunityMember(com.value)),
          ...Filter.el.leagues.filter(league => !Context.user.isLeagueMember(league.value))];
        inputs.forEach(el => el.disabled = Filter.el.onlyUser.checked);
        Calendar.update();
      };

      Filter.el.available.onchange = (e) => {
        Filter.el.userAvailable.disabled = !e.target.checked;
        Calendar.update();
      };

      Filter.el.userAvailable.onchange = (e) => {
        Calendar.update();
      };
    }
  }
}

/**
 * Each source hold a specific ajax request
 * that feeds the calendar.
 *
 * TODO: add color attribute to event
 * for rendering dots in the list view.
 */
class EventSource {
  /**
   * All sources are stored here on creation.
   */
  static objects = new Map();

  constructor({id, url}) {
    this.id = id;
    this.url = '/calendar/' + url;
    this.editable = false;
    EventSource.objects.set(id, this);
  }
  /**
   * We could transform event data received
   * from the server before add to the calendar.
   * Each extended class can have a 'transform' method.
   */
  eventDataTransform = (props) => {
    props.className = props.type + '-event';
    props.editable = this.editable;
    props.display = this.display(props);
    return this.transform ? this.transform(props) : props;
  }
  /**
   * Called each time the Filtering context changes.
   * Mainly used to determine event visibility on screen.
   */
  update = (e) => {
    e.setProp('display', this.display(e.extendedProps));
  }

  /**
   * Called right after the element has been added to the DOM.
   * If the event data changes, this is NOT called again.
   * Overrided by extended classes.
   */
  didMount() {}

  /** Render block by default */
  display = (e) => 'block';
}

/**
 * Public events can be seen by everyone.
 */
class PublicSource extends EventSource {
  static id = 'public';
  static url = 'get-public-events/';

  constructor() { super(PublicSource); }

  display = (e) => {
    const pk = e.community ? e.community.pk : null;
    const inCommunityPage = pk && Context.community && Context.community.pk === pk;
    const inCalendar = Filter.check.public && (pk && Filter.communities.includes(pk) || (!pk && Filter.check.osr));
    return inCommunityPage || inCalendar ? 'block' : 'none';
  }

  transform = (e) => {
    const {r, g, b, a} = hexToRgba(e.color || '#3788d8', 0.8);
    e.backgroundColor = `rgba(${r}, ${g}, ${b}, ${a})`;
    return e;
  }

  didMount(data) {
    const content = data.event.extendedProps.description;
    if (Calendar.object.view.type === 'listWeek' || Calendar.object.view.type === 'list') {
      const parent = data.el.querySelector('.fc-list-event-title');
      const el = document.createElement('span');
      el.innerHTML = `${content}`;
      parent.appendChild(el);
    } else if (content) {
      tippy(data.el, {content});
    }
  }
}

/**
 * Serves user's available event.
 * Refetched each time a event is created, updated or deleted.
 */
class UserAvailableSource extends EventSource {
  static id = 'available';
  static url = 'get-available-events/';

  constructor() {
    super(UserAvailableSource);
    this.url += Context.user.pk + '/'
    this.editable = true;
  }

  display = () =>
    Context.profil && Context.profil.pk === Context.user.pk
      ? 'block'
      : Filter.check.available
        ? Filter.check.userAvailable
          ? 'block' : 'background'
        : 'none';

  transform = (e) => {
    e.className = 'user-' + e.className;
    e.title = 'Me available';
    return e;
  }

  didMount(data) {
    if (data.event.display === 'block') {
      let vType = Calendar.object.view.type;
      let parent;
      let el = document.createElement('i');
      if (vType === 'listWeek' || vType === 'list') {
        parent = data.el.querySelector('.fc-list-event-title');
        el.className = 'icon-close-list glyphicon glyphicon-remove';
      } else {
        parent = data.el.querySelector('.fc-event-time');
        el.className = 'icon-close glyphicon glyphicon-remove';
      }
      el.onclick = () => Calendar.object.deleteAvailableEvent(data);
      parent.appendChild(el);
    }
  }
}

/**
 * Serves available events of user's opponents.
 * Refetched each time the Filter state change.
 * (events merging process happens on the server)
 */
class OpponentsAvailableSource extends EventSource {
  static id = 'opponents-available';
  static url = 'get-opponents-available-events/';

  constructor() {
    super(OpponentsAvailableSource);
    this.url += Context.user.pk + '/'
    this.extraParams = () => ({
      leagues: JSON.stringify(Filter.leagues)
    });
  }

  display = () =>
    Filter.check.available
      ? Calendar.object.view.type == 'listWeek' || Calendar.object.view.type == 'dayGridMonth'
        ? 'block' : 'background'
      : 'none';

  transform = (e) => {
    e.title = e.users.map(({name}) => name).join(', ');
    return e;
  }

  didMount(data) {
    const parent = data.el.querySelector('.fc-list-event-title');
    if (parent) {
      const plural = data.event.extendedProps.users.length > 1;
      const el = document.createElement('a');
      el.textContent = ` ${plural ? 'are' : 'is' } available`;
      parent.classList.add('available');
      parent.appendChild(el);
    }
  }
}

/**
 * Serves profil's available event.
 */
 class ProfilAvailableSource extends EventSource {
  static id = 'profil-available';
  static url = 'get-available-events/';

  constructor() {
    super(ProfilAvailableSource);
    this.url += Context.profil.pk + '/';
  }

  transform = (e) => {
    e.className = 'opponents-' + e.className;
    e.title = e.user.name + ' available';
    e.type = 'profil-' + e.type;
    return e;
  }
}

/**
 * Game request can be seen by involved players only.
 * Both of them can cancel/reject the event.
 * The receivers can also accept the request.
 * In those two cases, the game request is deleted.
 *
 * Even if the client is asked to select a division
 * when creating a game request, it is actually
 * optionnal (the model accepts empty division list).
 * Handy for hypothetic friendly challenge in the future.
 */
class GameRequestSource extends EventSource {
  static id = 'game-request';
  static url = 'get-game-request-events/';

  constructor() { super(GameRequestSource); }

  display = (e) =>
    Context.profil
      ? this.displayProfil(e)
      : Filter.check.request
        ? e.divisions.length
          ? e.divisions.map(({league}) => league.pk).some(pk => Filter.leagues.includes(pk))
            ? 'block' : 'none'
          :'block'
        : 'none'

  displayProfil = (e) =>
    e.receivers.map(({pk}) => pk).includes(Context.profil.pk) || e.sender.pk === Context.profil.pk ? 'block' : 'none';

  transform = (e) => {
    e.fromUser = Context.user.name === e.sender.name;
    e.className += e.fromUser ? '-user' : '';
    e.title = `
      ${e.sender.name} vs
      ${e.receivers.map(({name}) => name).join(', ')}`;
    return e;
  }

  didMount(data) {
    const divisions = data.event.extendedProps.divisions;
    const content = divisions.map(div => `${div.league.name} - ${div.name}`).join(', ');
    if (Calendar.object.view.type === 'listWeek' || Calendar.object.view.type === 'list') {
      const parent = data.el.querySelector('.fc-list-event-title');
      const el = document.createElement('span');
      el.innerHTML = `(${content})`;
      parent.appendChild(el);
    } else if (content) {
      tippy(data.el, {content});
    }
  }
}

/**
 * As public events, appointments can be seen by everyone
 * if its private attribute is not true. (else, only
 * involved users can see it)
 */
class AppointmentSource extends EventSource {
  static id = 'game-appointment';
  static url = 'get-game-appointment-events/';

  constructor() { super(AppointmentSource); }

  display = (e) => {
    const divs = e.divisions;
    const inCommunityPage = Context.community && divs.length && divs.filter(
      ({league}) => league.community && league.community.pk === Context.community.pk).length;
    const inProfil = Context.profil && e.users.map(({pk}) => pk).includes(Context.profil.pk);
    const inCalendar = Filter.check.appointment && (!divs.length || divs.map(
      ({league}) => league.pk).some(pk => Filter.leagues.includes(pk)));
    return inCommunityPage || inProfil || inCalendar ? 'block' : 'none';
  }

  displayProfil = (e) => e.users.map(({pk}) => pk).includes(Context.profil.pk) ? 'block' : 'none';

  transform = (e) => {
    e.hasUser = Context.user && e.users.map(({pk}) => pk).includes(Context.user.pk);
    e.className += e.hasUser ? '-user' : '';
    e.title = `${e.users[0].name} vs ${e.users[1].name}`;
    return e;
  }

  didMount(data) {
    const divisions = data.event.extendedProps.divisions;
    const content = divisions.map(div => `${div.league.name} - ${div.name}`).join(', ');
    if (Calendar.object.view.type === 'listWeek' || Calendar.object.view.type === 'list') {
      const parent = data.el.querySelector('.fc-list-event-title');
      const el = document.createElement('span');
      el.innerHTML = `(${content})`;
      parent.appendChild(el);
    } else if (content) {
      tippy(data.el, {content});
    }
  }
}

/**
 * Singleton wrapper for FullCalendar.
 */
 class Calendar extends FullCalendar.Calendar {

  /**
   * Sends a new ajax request and updates related event of the given source.
   * @param {EventSource} Source
   */
  static refetch(Source) {
    Calendar.object.getEventSourceById(Source.id).refetch();
  }

  static update() {
    const color = Filter.canEditAvailability
      ? 'rgba(227, 132, 113, 0.2)' : 'rgba(0, 0, 0, 0.1)';
    document.documentElement.style.setProperty('--selection-bg-color', color);
    Calendar.object.getEvents().forEach(e => {
      EventSource.objects.get(e.extendedProps.type).update(e);
    });
  }

  static get(key) {
    return Calendar.object.getOption(key);
  }

  static set(key, value) {
    Calendar.object.setOption(key, value);
  }

  static initialize(locale) {
    Calendar.object = new Calendar(locale);
    Calendar.object.render();
    if (!Context.profil && !Context.community) {
      Calendar.initializeTimeRangeSlider();
      Filter.initialize();
    }
  }

  static initializeTimeRangeSlider() {
    $(".fc-view-harness").first().before($("#time-range-selector-wrapper"));
    const from = $("#time-range-selector").attr('data-from');
    const to = $("#time-range-selector").attr('data-to');
    $("#time-range-selector").ionRangeSlider({
      type: "double",
      min: 0,
      max: 24,
      skin: "sharp",
      from, to,
      drag_interval: true,
      postfix: "h00",
      onStart: Calendar.object.setTimeRange,
      onFinish: Calendar.object.updateTimeRange
    });
  }

  constructor(locale) {

    /**
     * If a profil attribute exists in Context,
     * set the calendar to 'profil mode' and lists
     * all profil's related events.
     */
    const listOpts = {
      locale,
      allDaySlot: false,
      eventDisplay: 'block',
      initialView: 'list',
      duration: { weeks: 24 },
      headerToolbar: false,
      timeZone: 'UTC',
      height: 'auto',
    }

    const opts = {
      locale,
      height: 'auto',
      expandRows: false,
      allDaySlot: false,
      eventDisplay: 'block',
      initialView: 'dayGridMonth',
      headerToolbar: {
        left: 'prev,next today',
        center: 'title',
        right: 'dayGridMonth,timeGridWeek,listWeek'
      },
      selectMirror: true,
      timeZone: 'UTC',
      selectable: true,
    }

    super(
      document.getElementById('calendar'),
      Context.profil || Context.community ? listOpts : opts
    );

    this.setOption('viewDidMount', Calendar.update);
    this.setOption('eventDidMount', this.handleEventDidMount);
    this.setOption('eventClick', this.handleEventClick);
    this.addEventSource(new AppointmentSource());

    if (Context.user) {
      this.addEventSource(new GameRequestSource());
      this.addEventSource(new OpponentsAvailableSource());
      this.addEventSource(new UserAvailableSource());
    }

    if (Context.profil && (!Context.user || Context.user.pk !== Context.profil.pk)) {
      this.addEventSource(new ProfilAvailableSource());
    } else {
      this.addEventSource(new PublicSource());
      if (!Context.community) {
        this.setOption('select', this.createEvent);
        this.setOption('eventDrop', this.updateAvailableEvent);
        this.setOption('eventResize', this.updateAvailableEvent);
      }
    }
  }

  handleEventClick = (data) => {
    if (data.event.url) {
      data.jsEvent.preventDefault();
      window.open(data.event.url, "_blank");
    }

    switch (data.event.extendedProps.type) {
      case 'game-appointment':
        if (data.event.extendedProps.hasUser) {
          CancelGameAppointmentForm.init(data.event.extendedProps.pk);
        }
        break;

      case 'game-request':
        const Form = data.event.extendedProps.fromUser
          ? CancelGameRequestForm
          : AcceptGameRequestForm;
        Form.init(data.event.extendedProps.pk);
        break;
    }
  }

  handleEventDidMount = (data) => {
    if (data.event.extendedProps) {
      const src = EventSource.objects.get(data.event.extendedProps.type);
      if (src) {
        src.didMount(data)
      }
    }
  }

  setTimeRange = ({from, to}) => {
    const a = from.toString().padStart(2, '0');
    const b = to.toString().padStart(2, '0');
    this.setOption('slotMinTime', `${a}:00:00`);
    this.setOption('slotMaxTime', `${b}:00:00`);
  }

  updateTimeRange = ({from, to}) => {
    this.setTimeRange({from, to});
    $.post('/calendar/update-time-range-ajax/', {
      'start': from, 'end': to
    });
  }

  createEvent = (info) => {
    const min = this.getOption('slotMinTime');
    const max = this.getOption('slotMaxTime');
    let start = info.startStr;
    let end = info.endStr;
    if (info.view.type === 'dayGridMonth') {
      end = start;
      start += `T${min}Z`;
      end += `T${max}Z`;
    }
    if (info.start > Date.now() + 1000 * 60 * 60 * 2) {
      if (Filter.canEditAvailability) {
        this.createAvailableEvent(start, end);
      } else {
        CreateEventForm.init(start, end);
      }
    }
    this.unselect();
  }

  createAvailableEvent(start, end) {
    start = FullCalendarMoment.toMoment(start, this).format();
    end = FullCalendarMoment.toMoment(end, this).format();
    $.post(
      '/calendar/create-available-event/', { start, end },
      () => Calendar.refetch(UserAvailableSource)
    );
  }

  updateAvailableEvent = ({event}) => {
    let start = event.startStr;
    let end = event.endStr;
    let pk = event.extendedProps.pk;
    $.post(
      '/calendar/update-available-event/', { pk, start, end },
      () => Calendar.refetch(UserAvailableSource)
    );
  }

  deleteAvailableEvent = ({event}) => {
    const pk = event.extendedProps.pk
    $.post(
      '/calendar/delete-available-event/', { pk },
      () => Calendar.refetch(UserAvailableSource)
    );
  }
}

class CancelGameAppointmentForm {
  static el = {
    form: document.getElementById('cancel-game-appointment-form')
  }

  static init(pk) {
    CancelGameAppointmentForm.el.form.onsubmit = CancelGameAppointmentForm.handleSubmit(pk);
    MicroModal.show('cancel-game-appointment');
  }

  static handleSubmit = (pk) => (e) => {
    e.preventDefault(e);
    $.post('/calendar/cancel-game-ajax/', { pk }, () => {
      Calendar.refetch(AppointmentSource);
      MicroModal.close();
    });
  }
}

class CancelGameRequestForm {
  static el = {
    form: document.getElementById('cancel-game-request-form')
  }

  static init(pk) {
    CancelGameRequestForm.el.form.onsubmit = CancelGameRequestForm.handleSubmit(pk);
    MicroModal.show('cancel-game-request');
  }

  static handleSubmit = (pk) => (e) => {
    e.preventDefault(e);
    $.post('/calendar/cancel-game-request-ajax/', { pk }, () => {
      Calendar.refetch(GameRequestSource);
      MicroModal.close();
    });
  }
}

class AcceptGameRequestForm {
  static el = {
    confirm: document.getElementById('modal-accept-confirm'),
    reject: document.getElementById('modal-accept-reject')
  }

  static init(pk) {
    AcceptGameRequestForm.el.confirm.onclick =
    AcceptGameRequestForm.el.reject.onclick = AcceptGameRequestForm.handleClick(pk);
    MicroModal.show('accept-game-request');
  }

  static handleClick = (pk) => (e) => {
    e.preventDefault(e);
    if (e.target.id === "modal-accept-confirm") {
      $.post('/calendar/accept-game-request-ajax/', { pk }, () => {
        Calendar.refetch(GameRequestSource);
        Calendar.refetch(AppointmentSource);
      });
    } else {
      $.post('/calendar/reject-game-request-ajax/', { pk }, () => {
        Calendar.refetch(GameRequestSource);
      });
    }
    MicroModal.close();
  }
}

class CreateGameForm {
  static el = {
    form: document.getElementById('create-game-form'),
    playerSelect: document.getElementById('modal-player-select'),
    divisionSelect: document.getElementById('modal-division-select')
  }

  static get divisions() {
    return Array.from(document.getElementsByClassName('modal-division'))
      .filter(el => el.selected).map(el => el.value);
  }

  static init(type, dateStr) {
    CreateGameForm.el.form.classList.remove('hidden');
    CreateGameForm.el.form.onsubmit = CreateGameForm.handleSubmit(type, dateStr);
    CreateGameForm.el.playerSelect.onchange = CreateGameForm.handlePlayerChange;
  }

  static handlePlayerChange(e) {
    CreateGameForm.el.divisionSelect.textContent = '';
    Context.user.getDivisionIntersection(e.target.value).forEach(CreateGameForm.addDivision);
  }

  static addDivision(division) {
    const el = document.createElement('option');
    el.value = division.pk;
    el.className = 'modal-division';
    el.innerHTML = `${division.league.name} - ${division.name}`;
    document.getElementById('modal-division-select').appendChild(el);
  }

  static close() {
    CreateGameForm.el.divisionSelect.textContent = '';
    CreateGameForm.el.form.reset();
    CreateGameForm.el.form.classList.add('hidden');
  }

  static handleSubmit = (type, date) => (e) => {
    e.preventDefault();
    const receiver = CreateGameForm.el.playerSelect.value;
    const divisions = JSON.stringify(CreateGameForm.divisions);
    const isprivate = document.getElementById('modal-private').checked;
    $.post('/calendar/create-game/', {
      date,
      receiver,
      divisions,
      private: isprivate,
      type: type
    }, () => {
      Calendar.refetch(GameRequestSource);
      Calendar.refetch(AppointmentSource);
      CreateEventForm.close();
      MicroModal.close();
    });
  }
}

class CreateEventForm {
  static el = {
    startDate: document.getElementById('create-event-start-date'),
    endDate: document.getElementById('create-event-end-date'),
    type: document.getElementById('create-event-type-select'),
  }

  static format = (date) =>
    FullCalendar.formatDate(date, {
      month: 'long',
      year: 'numeric',
      day: 'numeric',
      hour: 'numeric',
      minute: 'numeric',
      timeZone: 'UTC',
    });

  static init(startStr, endStr) {
    CreateEventForm.el.type.onchange = CreateEventForm.handleTypeChange(startStr, endStr);
    CreateEventForm.el.startDate.textContent = CreateEventForm.format(startStr);
    CreateEventForm.el.endDate.textContent = CreateEventForm.format(endStr);
    MicroModal.show('create-event', {
      onClose: () => {
        CreateEventForm.close();
        CreateEventForm.el.type.selectedIndex = 0;
      }
    });
  }

  static close() {
    if (CreateEventForm.current) {
      CreateEventForm.current.close();
      CreateEventForm.current = null
    }
  }

  static handleTypeChange = (start, end) => (e) => {
    CreateEventForm.close();
    switch (e.target.value) {
      case 'game-request':
      case 'game-appointment':
        CreateEventForm.el.endDate.textContent =
          CreateEventForm.format(moment(start).add(90, 'm').utc().format());
        CreateEventForm.current = CreateGameForm;
        CreateGameForm.init(e.target.value, start)
        break;
    }
  }
}
