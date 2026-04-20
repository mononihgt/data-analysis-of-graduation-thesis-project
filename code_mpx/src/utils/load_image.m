function Ptex=load_image(win, path, picturename, ori)

    cd(path);
    picture = picturename;
    picture = imread(picture);
    Ptex = Screen('MakeTexture', win, picture); 
    cd(ori)

end