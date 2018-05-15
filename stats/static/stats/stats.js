function config_from_json(json, name){

var labels = json.map(function(e) {
  return moment(e.month).format('YYYY MM')
});

var values = json.map(function(e) {
  return e.total
});

var config = {
   type: 'line',
   data: {
      labels: labels,
      datasets: [{
         label: name,
         data: values,
         backgroundColor: 'rgba(0, 119, 204, 0.3)'
      }]
   },
   options: {
        scales: {
            xAxes: [{
                time: {
                  displayFormats: {
                          month: 'MMM YYYY'
                        }
                }
            }]
        }
    }
  }
return config
}
