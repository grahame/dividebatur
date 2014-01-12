angular.module('divideBaturFilters', []).filter('numberfmt', function() {
  var r = /\B(?=(\d{3})+(?!\d))/g;
  return function(input) {
    // http://stackoverflow.com/questions/2901102/how-to-print-a-number-with-commas-as-thousands-separators-in-javascript
    return (input || "").toString().replace(r, ",");
  };
}).filter('f2', function() {
    return function(input) {
        return (Math.round(input * 100) / 100).toString();
    };
});