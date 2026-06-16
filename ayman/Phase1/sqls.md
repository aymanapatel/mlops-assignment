|question|vLLM sql|golden sql|
|---|---|---|
|How many users received commentator badges in 2014?|SELECT COUNT(*) \nFROM badges \nWHERE badge_name = 'Commentator' \n  AND YEAR(creation_date) = 2014;|SELECT COUNT(Id) FROM badges WHERE Name = 'Commentator' AND STRFTIME('%Y', Date) = '2014'|
