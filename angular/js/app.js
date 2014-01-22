var divideBaturApp = angular.module('divideBaturApp', [
  'ngRoute',
  'divideBaturControllers',
  'divideBaturFilters',
  'divideBaturDirectives',
  'divideBaturServices'
]);

divideBaturApp.config(['$routeProvider',
  function($routeProvider) {
    $routeProvider.
      when('/index', {
        templateUrl: 'partials/count-list.html'
      }).
      when('/count/:countId', {
        templateUrl: 'partials/count-detail.html',
        controller: 'CountDetailCtrl'
      }).
      when('/count/:countId/round/:round', {
        templateUrl: 'partials/count-round-detail.html',
        controller: 'CountRoundDetailCtrl'
      }).
      otherwise({
        redirectTo: '/index'
      });
  }]);
