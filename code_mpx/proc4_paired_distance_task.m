try 
    clear all;
    
    %设置文件路径
    s = pwd;
    addpath(genpath(s));
    path.ori = s;
    path.face = [s '\Stimuli\face'];
    path.PDtask_data = [s '\PDtask_data'];
    path.intro = [s '\Stimuli\intro'];


    subinfo = getsubinfo;

    %% 
    % 设置参数
    [fix,key,rgb,win,winRect,width,height,sizes,Rect_PDtask,facebar,triallist] = load_PDpara();
    f = load('facelist.mat');
    f = f.facelist;
    facelist = f(str2double(char(subinfo(1))));
    facelist = facelist{1};
    % 加载图片 
    for i = 1:6
        Ftex{i}=load_image(win,path.face,facelist{i},path.ori);
    end
    dif_tex=load_image(win,path.intro,'dif.png',path.ori);
    mean_tex=load_image(win,path.intro,'mean.png',path.ori);
    mean_mean_tex = load_image(win,path.intro,'mean_mean.png',path.ori);

    %% 正式实验
    exp_intro_tex=load_image(win, path.intro, 'exp_intro.png', path.ori);
    [screenWidth, screenHeight] = Screen('WindowSize', win);
    [imageWidth, imageHeight] = Screen('WindowSize', exp_intro_tex);
    exp_intro_rect = CenterRectOnPoint([0, 0, imageWidth, imageHeight], screenWidth/2, screenHeight/2);
    Screen('Drawtexture',win,exp_intro_tex,[],exp_intro_rect);
    Screen('Flip', win);
    key_space(key)
        
    result=demo_PDtask(triallist,win,winRect,rgb,key,Ftex,Rect_PDtask.face,dif_tex,mean_tex,mean_mean_tex,Rect_PDtask.intro,Rect_PDtask.square,subinfo);

    %% 数据保存
    if ~isempty(result)
        columheader={'SubNo','Name','Gender','Age','Handedness',...
            'F1','F1V','F1X','F1Y','F2','F2V','F2X','F2Y','D','MidX','MidY','Mtask',...
            'DX','DY','ans_D','rt1','MX','MY','rt2','MMX','MMY','rt3'};
        result = orderfields(result,columheader);
        ret = [columheader;(struct2cell(result))'];
        cd(path.PDtask_data);
        currentDate = datestr(now, 'yyyy-mm-dd');

        T = cell2table(ret);
        csvFileName = ['PDtask-',char(subinfo(1)),'-',currentDate,'.csv']
        writetable(T, csvFileName, 'WriteVariableNames', false);
        % xlswrite(['PDtask-',char(subinfo(1)),'-',currentDate,'.xlsx'],ret);
        save(['PDtask-',char(subinfo(1)),'-',currentDate,'.mat'],'ret');
        cd(path.ori);
    else
        error('no data')
    end
    
    
    
    sca;


catch    
    ShowCursor;
    Screen('CloseAll');
    psychrethrow(lasterror);
end
