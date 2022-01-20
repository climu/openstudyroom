"use strict";
(function(osr_datatable_loader){
  // init function
  osr_datatable_loader.init = function(config){
    // create the datatable
    $('#'+config.id).DataTable({
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
})(window.osr_datatable_loader = window.osr_datatable_loader || {})