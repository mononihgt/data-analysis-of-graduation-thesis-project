AF={'af01.jpg','af03.jpg','af04.jpg','af08.jpg','af09.jpg','af11.jpg'};
AM={'am02.jpg','am03.jpg','am04.jpg','am06.jpg','am07.jpg','am08.jpg'};
for i=1:50
    n1 = randperm(6, 3);
    n2 = randperm(6, 3);
    facelist{i} = shuffle({AF{n1},AM{n2}});
end

