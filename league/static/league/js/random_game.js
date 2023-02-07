const slider_date = document.getElementById('slider_date');
const slider_rank = document.getElementById('slider_rank');
const startDateField = document.getElementById('id_start_date')
const endDateField = document.getElementById('id_end_date')
const startRankField = document.getElementById('id_start_rank')
const endRankField = document.getElementById('id_end_rank')


const now = new Date()

// Create array of ranks
let ranks = [];
for(let i=-30; i<9;i++){
  if (i<0){
    ranks.push(-i + 'k');
  }
  if (i>0){
    ranks.push(i + 'd');
  }
}

// Set the actual Date
function timestamp(str) {
    return new Date(str).getTime();
}

// Date in decimal
const formatDates = {
    to: function(value) {
        return new Date(Math.round(value)).toISOString().slice(0,10)
    },
    from: function (value) {
        return value;
    }
}

// Create date slider

const date_min = now.setMonth(now.getMonth()-3)
const date_max = new Date().getTime()

const start_date = new Date(startDateField.value).getTime()
const end_date = new Date(endDateField.value).getTime()
noUiSlider.create(slider_date, {
    start: [start_date, end_date],
    connect: true,
    range: {
        // Set month min 3 months from current date
        min: date_min,
        max: date_max        
    },
    pips: { mode: 'steps', format: formatDates },
    format: formatDates
})

// Listen values of dates slider
slider_date.noUiSlider.on('update', function () { 
    const [start, end] = slider_date.noUiSlider.get()
    startDateField.value = start
    endDateField.value = end    
    document.getElementById('date_min').textContent = start
    document.getElementById('date_max').textContent = end
})

// Set the ranks format
const formatRanks = {
    to: function(value) {
        return ranks[Math.round(value)]
    },
    from: function (value) {
        return ranks.indexOf(value);
    }
}

// Create ranks slider
noUiSlider.create(slider_rank, {
    start: [startRankField.value, endRankField.value],
    connect: true,
    range: { min: 0, max: ranks.length - 1 },
    step: 1,
    format: formatRanks,
    pips: { mode: 'steps', format: formatRanks, density: 50 },
})

// Listen values of ranks slider
slider_rank.noUiSlider.on('update', function () { 
    const [start, end] = slider_rank.noUiSlider.get()
    startRankField.value = start
    endRankField.value = end    
    document.getElementById('rank_min').textContent = start
    document.getElementById('rank_max').textContent = end
    
})
