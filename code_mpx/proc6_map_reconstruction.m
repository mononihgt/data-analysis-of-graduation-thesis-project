try
    clear all;

    %设置文件路径
    s = pwd;
    addpath(genpath(s));
    path.ori = s;
    path.face = [s '\Stimuli\face'];
    path.intro = [s '\Stimuli\intro'];
    path.MRtask_data = [s '\MRtask_data'];

    subinfo = getsubinfo;

%% 
    % 设置参数
    [fix,key,rgb,win,winRect,width,height,sizes,facevalue,FRect,line,dot] = load_MRpara();
    f = load('facelist.mat');
    f = f.facelist;
    facelist = f(str2double(char(subinfo(1))));
    facelist = facelist{1};
    % 加载图片 
    for i = 1:6
        Ftex{i}=load_image(win,path.face,facelist{i},path.ori);
    end
    position = shuffle(1:6);

%% 复现轴及范围
    [Xlength,Ylength,Xrange,Yrange]=adjust_axes(win,key,Ftex,FRect,line,dot,position);

%% 复现坐标（坐标+村庄）

    result=point_reconstruct(win,Ftex,FRect,line,dot,Xrange,Yrange,position);
    
    if str2double(char(subinfo(2))) == 1
        Gender = 'Male';
    else
        Gender = 'Female';
    end
    %-------------------------------------------
    if str2double(char(subinfo(5))) == 1
        Handedness = 'Right';
    else
        Handedness = 'Left';
    end
    result.SubNo = str2double(char(subinfo(1)));
    result.Name = char(subinfo(4));
    result.Gender = Gender;
    result.Age = str2double(char(subinfo(3)));
    result.Handedness = Handedness;
    result.Xrange=Xrange;
    result.Yrange=Yrange;

%% 数据保存
    
    if ~isempty(result)
        columheader={'SubNo','Name','Gender','Age','Handedness','Xrange','Yrange',...
            'F1X','F1Y','F1V','F2X','F2Y','F2V','F3X','F3Y','F3V',...
            'F4X','F4Y','F4V','F5X','F5Y','F5V','F6X','F6Y','F6V'};
        result = orderfields(result,columheader);
        ret = [columheader;(struct2cell(result))'];
        cd(path.MRtask_data);
        currentDate = datestr(now, 'yyyy-mm-dd');
        T = cell2table(ret);
        csvFileName = ['MRtask-',char(subinfo(1)),'-',currentDate,'.csv']
        writetable(T, csvFileName, 'WriteVariableNames', false);
        % xlswrite(['MRtask-',char(subinfo(1)),'-',currentDate,'.xlsx'],ret);
        save(['MRtask-',char(subinfo(1)),'-',currentDate,'.mat'],'ret');
    end

    cd(path.ori)
    sca;

catch    
    ShowCursor;
    Screen('CloseAll');
    psychrethrow(lasterror);
end
