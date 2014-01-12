var divideBaturApp = angular.module('divideBaturApp', [
  'ngRoute',
  'divideBaturControllers'
]);
 
divideBaturApp.config(['$routeProvider',
  function($routeProvider) {
    $routeProvider.
      when('/index', {
        templateUrl: 'partials/count-list.html',
        controller: 'CountListCtrl'
      }).
      otherwise({
        redirectTo: '/index'
      });
  }]);
