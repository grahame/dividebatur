var divideBaturApp = angular.module('divideBaturApp', [
  'ngRoute',
  'ui.bootstrap',
  'divideBaturControllers',
  'divideBaturFilters',
  'divideBaturDirectives'
]);

divideBaturApp.config(['$routeProvider',
  function($routeProvider) {
    $routeProvider.
      when('/index', {
        templateUrl: 'partials/count-list.html',
        controller: 'CountListCtrl'
      }).
      when('/count/:countId', {
        templateUrl: 'partials/count-detail.html',
        controller: 'CountDetailCtrl'
      }).
      otherwise({
        redirectTo: '/index'
      });
  }]);
