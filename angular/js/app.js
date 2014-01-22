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
      when('/scenario/:countId', {
        templateUrl: 'partials/count-detail.html',
        controller: 'CountDetailCtrl'
      }).
      when('/scenario/:countId/count/:round', {
        templateUrl: 'partials/count-round-detail.html',
        controller: 'CountRoundDetailCtrl'
      }).
      otherwise({
        redirectTo: '/index'
      });
  }]);
