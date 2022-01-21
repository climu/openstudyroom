"use strict";
(function(osr_datatable_loader){
  // closure var
  let datatable = undefined

  // init function
  osr_datatable_loader.init = function(config){
    // create the datatable
    datatable = $('#'+config.id).DataTable({
      ajax: {
        url: config.url,
        dataSrc: 'data'
      },
      columns: config.columns.map(function(el){ 
        return {
          data: el.key
        }
      })
    });


  }
  // update data source
  osr_datatable_loader.update_data_source = function(new_url){
    datatable.clear().draw()
    datatable.ajax.url(new_url)
    datatable.ajax.reload()
  }
})(window.osr_datatable_loader = window.osr_datatable_loader || {})