const _conf=(function () {
    /*   configuration backend */
    const ipBackEnd='geoai-solutions.ddns.net';
    const portBackend='3001';

    /*   configuration server données "Vecteur" */
    const ipDataServer='geoai-solutions.ddns.net';
    const portDataServer='5480';
   return{
       _endPointApi:`http://${ipBackEnd}:${portBackend}`,
       _endPointDataServer:`http://${ipDataServer}:${portDataServer}/geocarte`
   }
})()