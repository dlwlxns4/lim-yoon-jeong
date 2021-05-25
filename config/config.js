module.exports = {
    server_port:3300,
    admin_id:'lim-yoon-jeong',
    admin_password:'2021',
    route_info: [
        {file:'./index', path:'/', method:'index', type:'get'},
        {file:'./admin', path:'/adminLogin', method:'adminLogin', type:'post'},
        {file:'./admin', path:'/admin', method:'admin', type:'get'},
        {file:'./admin', path:'/admin/list', method:'list', type:'get'},
        {file:'./admin', path:'/admin/list/show/:userCode', method:'show', type:'get'},
        {file:'./admin', path:'/admin/list/show', method:'showHistory', type:'post'},
        {file:'./admin', path:'/admin/logout', method:'logout', type:'get'},
        {file:'./attendance', path:'/process/list', method:'list', type:'post'},
        {file:'./faceRecognition', path:'/process/recognition', method:'recognition', type:'post'}
    ]                           
};