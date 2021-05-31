function hexToRgb(hex) {
  var result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? {
    r: parseInt(result[1], 16),
    g: parseInt(result[2], 16),
    b: parseInt(result[3], 16)
  } : null;
}

/**
 * Contains data sent by the server.
 * { user, communitites, divisions }
 */
class Context {
  constructor(){
    const ctxData = JSON.parse(document.getElementById('context-data').textContent);
    this.communities = ctxData.communities;
    this.leagues = ctxData.leagues;
    this.user = ctxData.user ? new User(ctxData) : null;
  }
}

class User {
  constructor(ctxData) {
    Object.assign(this, ctxData.user);
  }
  inLeague = ({value}) => {
    return !!this.divisions.filter(div =>
      div.league.pk === parseInt(value)).length;
  }
  inCommunity = ({value}) => {
    return !!this.communities.filter(com =>
      com.pk === parseInt(value)).length;
  }
  /**
   * Used by the CreateGameRequestForm
   * for feed its select options.
   */
   getDivisionsWithOpponent = (user_pk) => {
    return Array.from(this.divisions)
      .filter(div => div.users
        .map(({ pk }) => pk)
        .includes(user_pk));
  }
}

/**
 * Each source hold a specific ajax request
 * that feeds the calendar. Miam !
 *
 * eventUpdate method is called is time the
 * filtering context changes.
 *
 * eventDataTransform method is called each time
 * a update event is sent by the server.
 */

/**
 * TODO: add color attribute to event
 * for rendering dots in the list view.
 */
class EventSource {
  static objects = new Map();

  constructor(ctx, calendar, id, url) {
    EventSource.objects.set(id, this);
    this.id = id;
    this.url = '/calendar/' + url + '/';
    this.ctx = ctx;
    this.calendar = calendar;
  }

  eventUpdate(e) {}

  eventDataTransform(e) {
    return {...e, className: `${e.type}-event`};
  }
}

class PublicEventSource extends EventSource {
  static id = 'public';
  constructor(ctx, calendar) {
    super(ctx, calendar, PublicEventSource.id, 'get-public-events');
  }
  visible({community}) {
    return Input.public.checked
      ? community
        ? Input.values(Input.communities).includes(community.pk)
        : Input.osr.checked
      : false;
  }
  eventDataTransform = (e) => {
    e = super.eventDataTransform(e);
    e.display = this.visible(e) ? 'block' : 'none';
    const {r, g, b} = hexToRgb(e.color || '#3788d8');
    e.backgroundColor = `rgba(${r}, ${g}, ${b}, 0.8)`;
    return e;
  }
  eventUpdate = (e) => {
    const visible = this.visible(e.extendedProps);
    e.setProp('display', visible ? 'block' : 'none');
  }
}

class UserAvailableEventSource extends EventSource {
  static id = 'user-available';
  constructor(ctx, calendar) {
    super(ctx, calendar, UserAvailableEventSource.id, 'get-user-available-events');
  }
  get visible() {
    return Input.userAvailable.checked && Input.available.checked;
  }
  get display() {
    return Input.available.checked
      ? Input.userAvailable.checked
        ? 'block'
        : 'background'
      : 'none';
  }
  eventDataTransform = (e) => {
    e = super.eventDataTransform(e);
    e.editable = true;
    e.display = this.display;
    return e;
  }
  eventUpdate = (e) => {
    e.setProp('display', this.display);
  }
}

class AvailableEventSource extends EventSource {
  static id = 'available';
  constructor(ctx, calendar) {
    super(ctx, calendar, AvailableEventSource.id, 'get-available-events');
    this.extraParams = () => ({
      leagues: JSON.stringify(Input.values(Input.leagues))
    });
  }
  visible() {
    return Input.available.checked;
  }
  eventDataTransform = (e) => {
    e = super.eventDataTransform(e);
    e.title = e.users.map(user => user.name).join(', ');
    e.display = this.visible() ? 'background' : 'none';
    return e;
  }
  eventUpdate = (e) => {
    const visible = this.visible();
    e.setProp('display', visible ? 'background' : 'none');
  }
}

class RequestEventSource extends EventSource {
  static id = 'game-request';
  constructor(ctx, calendar) {
    super(ctx, calendar, RequestEventSource.id, 'get-game-request-events');
  }
  visible({divisions}) {
    return Input.gameRequest.checked
      ? divisions.length
        ? divisions.map(div => div.league.pk).some(pk => Input.values(Input.leagues).includes(pk))
        : true
      : false;
  }
  eventDataTransform = (e) => {
    e = super.eventDataTransform(e);
    e.isUser = this.ctx.user.name === e.sender.name;
    e.className += e.isUser ? '-user' : '';
    e.title = `${e.sender.name} vs
      ${e.receivers.map(({name}) => name).join(', ')}
      (${e.divisions.map(div => div.name).join(', ')})`
    e.display = this.visible(e) ? 'block' : 'none';
    return e;
  }
  eventUpdate = (e) => {
    const visible = this.visible(e.extendedProps);
    e.setProp('display', visible ? 'block' : 'none');
  }
}

class AppointmentEventSource extends EventSource {
  static id = 'game-appointment';
  constructor(ctx, calendar) {
    super(ctx, calendar, AppointmentEventSource.id, 'get-game-appointment-events');
  }
  visible({divisions}) {
    return Input.appointment.checked
      ? divisions.length
        ? divisions.map(div => div.league.pk).some(pk => Input.values(Input.leagues).includes(pk))
        : true
      : false;
  }
  eventDataTransform = (e) => {
    e = super.eventDataTransform(e);
    e.isUser = e.users.map(({pk}) => pk).includes(this.ctx.user.pk);
    e.className += e.isUser ? '-user' : '';
    e.title = `${e.users[0].name} vs ${e.users[1].name}
      (${e.divisions.map(div => div.name).join(', ')})`;
    e.display = this.visible(e) ? 'block' : 'none';
    return e;
  }
  eventUpdate = (e) => {
    const visible = this.visible(e.extendedProps);
    e.setProp('display', visible ? 'block' : 'none');
  }
}

/**
 * Just a basic wrapper for FullCalendar
 */
class Calendar extends FullCalendar.Calendar {
  constructor(ctx, modal) {
    const container = document.getElementById('calendar');
    super(container, {
      //themeSystem: 'bootstrap',
      height: 'auto',
      expandRows: false,
      allDaySlot: false,
      eventDisplay: 'block',
      initialView: 'timeGridWeek',
      headerToolbar: {
        left: 'prev,next today',
        center: 'title',
        right: 'dayGridMonth,timeGridWeek,listWeek'
      },
      selectMirror: true,
      timeZone: 'UTC',
    });
    this.ctx = ctx;
    this.modal = modal;
    this.setOption('select', this.createEvent);
    this.setOption('eventDrop', this.saveEvent);
    this.setOption('eventResize', this.saveEvent);
    this.setOption('eventClick', this.handleEventClick);
    this.setOption('dateClick', this.handleDateClick);
    this.render();
    this.initializeSources();
    // circular dependencies work arround
    Calendar.object = this;
  }

  cancelGameAppointment = (e) => {
    this.modal.cancelGameAppointmentForm.pk = e.extendedProps.pk;
    this.modal.show(CancelGameAppointmentForm);
  }

  cancelGameRequest = (e) => {
    this.modal.cancelGameRequestForm.pk = e.extendedProps.pk;
    this.modal.show(CancelGameRequestForm);
  }

  updateGameRequest = (e) => {
    this.modal.updateGameRequestForm.pk = e.extendedProps.pk;
    this.modal.show(UpdateGameRequestForm);
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
    start = FullCalendarMoment.toMoment(start, this).format()
    end = FullCalendarMoment.toMoment(end, this).format()
    $.post('/calendar/create-available-event/', { start, end },
      () => this.getEventSourceById(UserAvailableEventSource.id).refetch());
    this.unselect();
  }

  deleteEvent = ({event}) => {
    const pk = event.extendedProps.pk
    $.post('/calendar/delete-available-event/', { pk },
      () => this.getEventSourceById('user-available').refetch());
  }

  saveEvent = ({event}) => {
    let start = event.startStr;
    let end = event.endStr;
    let pk = event.extendedProps.pk;
    $.post('/calendar/update-available-event/', { pk, start, end },
      () => this.getEventSourceById(UserAvailableEventSource.id).refetch());
  }

  handleDateClick = (info) => {
    // a game request cannot be create before the next two hour
    const minTime = Date.now() + 1000 * 60 * 60 * 2;
    if (!this.getOption('selectable') && this.modal && info.date > minTime) {
      const formated = FullCalendar.formatDate(info.dateStr, {
        month: 'long',
        year: 'numeric',
        day: 'numeric',
        hour: 'numeric',
        minute: 'numeric',
        timeZone: 'UTC',
      });
      this.modal.createGameRequestForm.setDate(info.dateStr);
      this.modal.show(CreateGameRequestForm, formated);
    }
  }

  handleEventClick = ({event}) => {
    switch (event.extendedProps.type) {
      case 'user-available':
        Input.userAvailable.checked
          ? this.deleteEvent({event})
          : null;
        break;
      case 'game-request':
        event.extendedProps.isUser
          ? this.cancelGameRequest(event)
          : this.updateGameRequest(event);
        break;
      case 'game-appointment':
        event.extendedProps.isUser
          ? this.cancelGameAppointment(event)
          : null;
        break;
      }
  }

  updateEvents = () => {
    this.getEvents().forEach(e => {
      EventSource.objects
        .get(e.extendedProps.type)
        .eventUpdate(e);
    });
  }

  setTimeRange = ({from, to}) => {
    const a = from.toString().padStart(2, '0');
    const b = to.toString().padStart(2, '0');
    calendar.setOption('slotMinTime', `${a}:00:00`);
    calendar.setOption('slotMaxTime', `${b}:00:00`);
  }

  updateTimeRange = ({from, to}) => {
    this.setTimeRange({from, to});
    $.post('/calendar/update-time-range-ajax/', {
      'start': from,
      'end': to
    });
  }

  initializeSources = () => {
    this.addEventSource(new PublicEventSource(this.ctx, this));
    if (this.ctx.user) {
      this.addEventSource(new AvailableEventSource(this.ctx, this));
      this.addEventSource(new UserAvailableEventSource(this.ctx, this));
      this.addEventSource(new RequestEventSource(this.ctx, this));
      this.addEventSource(new AppointmentEventSource(this.ctx, this));
    }
  }
}

/**
 * Utilities for handling input changes
 */
class Input {

  // returns values of a checkbox's group
  static values(elements) {
    return elements.filter(el => !el.disabled && el.checked).map(el => parseInt(el.value));
  }

  static get onlyUser() {
    return document.getElementById('only-user-filter');
  }

  static get osr() {
    return document.getElementById('osr-filter');
  }

  static get communities() {
    return Array.from(document.getElementsByClassName('community-filter'));
  }

  static get leagues() {
    return Array.from(document.getElementsByClassName('league-filter'));
  }

  static get public() {
    return document.getElementById('public-filter');
  }

  static get appointment() {
    return document.getElementById('appointment-filter');
  }

  static get gameRequest() {
    return document.getElementById('game-request-filter');
  }

  static get available() {
    return document.getElementById('av-event-filter');
  }

  static get userAvailable() {
    return document.getElementById('user-av-event-filter');
  }

}

class ModalManager {
  constructor(ctx) {
    MicroModal.init();
    this.createGameRequestForm = new CreateGameRequestForm(ctx, this);
    this.cancelGameRequestForm = new CancelGameRequestForm(ctx, this);
    this.updateGameRequestForm = new UpdateGameRequestForm(ctx, this);
    this.cancelGameAppointmentForm = new CancelGameAppointmentForm(ctx, this);
  }
  static get title() {
    return document.getElementById('modal-title');
  }
  changeType = (e) => {
    //ModalForm[this.event].classList.add('hidden');
    //ModalForm[e.target.value].classList.remove('hidden');
    this.event = e.target.value;
  }
  show = (Form, title) => {
    CreateGameRequestForm.form.classList.toggle(
      'hidden', Form != CreateGameRequestForm);
    CancelGameRequestForm.form.classList.toggle(
      'hidden', Form != CancelGameRequestForm);
    UpdateGameRequestForm.form.classList.toggle(
      'hidden', Form != UpdateGameRequestForm);
    CancelGameAppointmentForm.form.classList.toggle(
      'hidden', Form != CancelGameAppointmentForm);
    ModalManager.title.textContent = Form.form.dataset.title;
    CreateGameRequestForm.date.textContent = title;
    MicroModal.show('cal-modal');
  }
  close = () => {
    MicroModal.close('cal-modal');
  }
}

class CancelGameAppointmentForm {
  static type = 'cancel-appointment';
  constructor(ctx, modal) {
    this.ctx = ctx;
    this.modal = modal;
    this.pk = null;
    CancelGameAppointmentForm.form.onsubmit = this.handleSubmit;
  }

  static get form() {
    return document.getElementById('modal-cancel-game-appointment');
  }

  handleSubmit = (e) => {
    e.preventDefault(e);
    $.post('/calendar/cancel-game-ajax/', { pk: this.pk }, () => {
      Calendar.object.getEventSourceById(AppointmentEventSource.id).refetch();
      this.modal.close();
    });
  }
}

class CancelGameRequestForm {
  static type = 'cancel-request';
  constructor(ctx, modal) {
    this.ctx = ctx;
    this.modal = modal;
    CancelGameRequestForm.form.onsubmit = this.handleSubmit;
  }

  static get form() {
    return document.getElementById('modal-cancel-game-request');
  }

  handleSubmit = (e) => {
    e.preventDefault(e);
    $.post('/calendar/cancel-game-request-ajax/', { pk: this.pk }, () => {
      Calendar.object.getEventSourceById(RequestEventSource.id).refetch();
      this.modal.close();
    });
  }
}

class UpdateGameRequestForm {
  static type = 'update-request';
  constructor(ctx, modal) {
    this.ctx = ctx;
    this.modal = modal;
    UpdateGameRequestForm.confirm.onclick = this.handleClick;
    UpdateGameRequestForm.reject.onclick = this.handleClick;
  }

  static get confirm() {
    return document.getElementById('modal-accept-confirm');
  }

  static get reject() {
    return document.getElementById('modal-accept-reject');
  }

  static get form() {
    return document.getElementById('modal-accept-game-request');
  }

  handleClick = (e) => {
    e.preventDefault(e);
    if (e.target.id === "modal-accept-confirm") {
      $.post('/calendar/accept-game-request-ajax/', { pk: this.pk,  }, () => {
        Calendar.object.getEventSourceById(RequestEventSource.id).refetch();
        Calendar.object.getEventSourceById(AppointmentEventSource.id).refetch();
        this.modal.close();
      });
    } else {
      $.post('/calendar/reject-game-request-ajax/', { pk: this.pk,  }, () => {
        Calendar.object.getEventSourceById(RequestEventSource.id).refetch();
        this.modal.close();
      });
    }
  }
}

class CreateGameRequestForm {
  static type = 'create';
  constructor(ctx, modal) {
    this.ctx = ctx;
    this.modal = modal;
    ctx.user.opponents.forEach(CreateGameRequestForm.addPlayer)
    CreateGameRequestForm.playerSelect.onchange = this.handlePlayerChange;
    CreateGameRequestForm.form.onsubmit = this.handleSubmit;
    this.date = null;
  }

  static get form() {
    return document.getElementById('modal-create-game-request');
  }

  static get date() {
    return document.getElementById('modal-date');
  }

  static get playerSelect() {
    return document.getElementById('modal-player');
  }

  static get divisionSelect() {
    return document.getElementById('modal-divisions-select');
  }

  static get privateEl() {
    return document.getElementById('modal-private');
  }

  static get divisions() {
    return Array.from(document.getElementsByClassName('modal-division'))
      .filter(el => el.selected)
      .map(el => el.value);
  }

  static addPlayer(user) {
    const el = document.createElement('option')
    el.value = user.pk;
    el.innerHTML = user.name;
    CreateGameRequestForm.playerSelect.appendChild(el);
  }

  static addDivision(division) {
    const el = document.createElement('option');
    el.value = division.pk;
    el.className = 'modal-division';
    el.innerHTML = division.name;
    CreateGameRequestForm.divisionSelect.appendChild(el);
  }

  setDate = (date) => {
    this.date = date;
    CreateGameRequestForm.date.textContent = this.date;
  }

  handleSubmit = (e) => {
    e.preventDefault();
    const date = this.date;
    const receiver = CreateGameRequestForm.playerSelect.value;
    const divisions = JSON.stringify(CreateGameRequestForm.divisions);
    const isprivate = CreateGameRequestForm.privateEl.checked;
    $.post('/calendar/create-game-request2/',
    {
      date,
      receiver,
      divisions,
      private: isprivate
    }, () => {
      CreateGameRequestForm.divisionSelect.textContent = '';
      Calendar.object.getEventSourceById(RequestEventSource.id).refetch();
      CreateGameRequestForm.form.reset();
      this.modal.close();
    });
  }

  handlePlayerChange = (e) => {
    CreateGameRequestForm.divisionSelect.textContent = '';
    this.ctx.user
      .getDivisionsWithOpponent(parseInt(e.target.value))
      .forEach(CreateGameRequestForm.addDivision);
    //GameRequestForm.divisionSelect.classList.toggle(
      //'hidden', !GameRequestForm.divisionSelect.childElementCount);
  }
}

function initializeTimeRangeSlider() {
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
    onStart: calendar.setTimeRange,
    onFinish: calendar.updateTimeRange
  });
}

// Make a class of it
function initializeInputs(calendar, ctx) {
  function handleOnlyUserChanged(e) {
    const inputs = [
      ..._.reject(Input.communities, ctx.user.inCommunity),
      ..._.reject(Input.leagues, ctx.user.inLeague)];
    inputs.forEach(el => el.disabled = e.target.checked);
    calendar.updateEvents();
  }

  Input.communities.forEach(el => el.onchange = calendar.updateEvents);
  Input.leagues.forEach(el => el.onchange = () => {
    calendar.getEventSourceById(AvailableEventSource.id).refetch();
    calendar.updateEvents();
  });

  if (ctx.user) {
    Input.onlyUser.onchange = handleOnlyUserChanged;
    Input.gameRequest.onchange = calendar.updateEvents;
    Input.available.onchange = (e) => {
      calendar.setOption('selectable', e.target.checked && Input.userAvailable.checked);
      Input.userAvailable.disabled = !e.target.checked;
      calendar.updateEvents();
    }
    Input.userAvailable.onchange = (e) => {
      calendar.setOption('selectable', e.target.checked && Input.available.checked);
      calendar.updateEvents();
    }
  }

  Input.appointment.onchange = calendar.updateEvents;
  Input.osr.onchange = calendar.updateEvents;
  Input.public.onchange = calendar.updateEvents;
}

// serve data from server
const ctx = new Context();

// disable crud operations for anonym user
const modal = ctx.user ? new ModalManager(ctx) : null;

// initialize calendar
const calendar = new Calendar(ctx, modal);

initializeInputs(calendar, ctx);
initializeTimeRangeSlider();